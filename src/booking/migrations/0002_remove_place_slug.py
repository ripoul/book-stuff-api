from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("booking", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="place",
            name="slug",
        ),
    ]
