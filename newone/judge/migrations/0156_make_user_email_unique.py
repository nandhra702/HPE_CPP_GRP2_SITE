# Generated manually to make auth_user email field unique

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0155_alter_bulkemailcampaign_options_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            # First, handle any duplicate emails by appending _duplicate_{id}
            sql="""
                UPDATE auth_user u1
                INNER JOIN (
                    SELECT email, MIN(id) as keep_id
                    FROM auth_user
                    WHERE email != '' AND email IS NOT NULL
                    GROUP BY email
                    HAVING COUNT(*) > 1
                ) u2 ON u1.email = u2.email
                SET u1.email = CONCAT(u1.email, '_duplicate_', u1.id)
                WHERE u1.id != u2.keep_id;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            # Add unique constraint to email field
            sql="""
                ALTER TABLE auth_user 
                ADD UNIQUE INDEX unique_email (email);
            """,
            reverse_sql="""
                ALTER TABLE auth_user 
                DROP INDEX unique_email;
            """,
        ),
    ]
