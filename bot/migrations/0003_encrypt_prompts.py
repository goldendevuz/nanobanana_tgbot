"""Encrypt prompts and result images at rest, and backfill existing rows.

Raw SQL is used deliberately: reading through the ORM would push the legacy
plaintext through EncryptedTextField.from_db_value, which would fail to decrypt it.
"""

import bot.fields
from bot.crypto import decrypt, encrypt, fingerprint, is_encrypted
from django.db import migrations, models


def encrypt_existing(apps, schema_editor):
    table = apps.get_model("bot", "GenerationTask")._meta.db_table
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f"SELECT id, prompt, result_url FROM {table}")
        rows = cursor.fetchall()

        for pk, prompt, result_url in rows:
            prompt = prompt or ""
            result_url = result_url or ""
            if is_encrypted(prompt) and (not result_url or is_encrypted(result_url)):
                continue  # already migrated
            cursor.execute(
                f"UPDATE {table} SET prompt = %s, result_url = %s, "
                f"prompt_fingerprint = %s, prompt_length = %s WHERE id = %s",
                [
                    encrypt(prompt) if not is_encrypted(prompt) else prompt,
                    encrypt(result_url) if result_url and not is_encrypted(result_url) else result_url,
                    fingerprint(prompt),
                    len(prompt),
                    pk,
                ],
            )


def decrypt_existing(apps, schema_editor):
    table = apps.get_model("bot", "GenerationTask")._meta.db_table
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f"SELECT id, prompt, result_url FROM {table}")
        for pk, prompt, result_url in cursor.fetchall():
            cursor.execute(
                f"UPDATE {table} SET prompt = %s, result_url = %s WHERE id = %s",
                [
                    decrypt(prompt) if is_encrypted(prompt or "") else (prompt or ""),
                    decrypt(result_url) if is_encrypted(result_url or "") else (result_url or ""),
                    pk,
                ],
            )


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0002_telegramuser_language_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='generationtask',
            name='prompt_fingerprint',
            field=models.CharField(blank=True, db_index=True, help_text='Keyed digest of the prompt — identifies a repeated prompt without revealing it.', max_length=32),
        ),
        migrations.AddField(
            model_name='generationtask',
            name='prompt_length',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='generationtask',
            name='prompt',
            field=bot.fields.EncryptedTextField(),
        ),
        migrations.AlterField(
            model_name='generationtask',
            name='result_url',
            field=bot.fields.EncryptedTextField(blank=True),
        ),
        migrations.RunPython(encrypt_existing, decrypt_existing),
    ]
