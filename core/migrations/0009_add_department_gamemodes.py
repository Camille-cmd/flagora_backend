# Generated manually for department gamemode

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_userpreferencegamemode'),
    ]

    operations = [
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Department name')),
                ('number', models.CharField(max_length=3, unique=True, verbose_name='Department number')),
                ('region', models.CharField(max_length=100, verbose_name='Region')),
                ('prefecture', models.CharField(max_length=100, verbose_name='Prefecture')),
            ],
            options={
                'verbose_name': 'department',
                'verbose_name_plural': 'departments',
                'ordering': ('number',),
            },
        ),
        migrations.CreateModel(
            name='UserDepartmentScore',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('game_mode', models.CharField(choices=[('GCFF_TRAINING_INFINITE', 'Guess Country From Flag - Training Infinite'), ('GCFF_CHALLENGE_COMBO', 'Guess Country From Flag - Challenge Combo'), ('GCFC_TRAINING_INFINITE', 'Guess Capital From Country - Training Infinite'), ('GCFC_CHALLENGE_COMBO', 'Guess Capital From Country - Challenge Combo'), ('GDFN_TRAINING_INFINITE', 'Guess Department From Number - Training Infinite'), ('GDFN_CHALLENGE_COMBO', 'Guess Department From Number - Challenge Combo')], verbose_name='game mode')),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='department_scores', to='core.department', verbose_name='department')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_department_scores', to=settings.AUTH_USER_MODEL, verbose_name='user')),
                ('user_guesses', models.ManyToManyField(blank=True, related_name='user_department_scores', to='core.guess', verbose_name='user guesses')),
            ],
            options={
                'verbose_name': 'user department score',
                'verbose_name_plural': 'user department scores',
                'ordering': ('created_at',),
            },
        ),
        migrations.AlterField(
            model_name='usercountryscore',
            name='game_mode',
            field=models.CharField(choices=[('GCFF_TRAINING_INFINITE', 'Guess Country From Flag - Training Infinite'), ('GCFF_CHALLENGE_COMBO', 'Guess Country From Flag - Challenge Combo'), ('GCFC_TRAINING_INFINITE', 'Guess Capital From Country - Training Infinite'), ('GCFC_CHALLENGE_COMBO', 'Guess Capital From Country - Challenge Combo'), ('GDFN_TRAINING_INFINITE', 'Guess Department From Number - Training Infinite'), ('GDFN_CHALLENGE_COMBO', 'Guess Department From Number - Challenge Combo')], verbose_name='game mode'),
        ),
        migrations.AlterField(
            model_name='userpreferencegamemode',
            name='game_mode',
            field=models.CharField(choices=[('GCFF_TRAINING_INFINITE', 'Guess Country From Flag - Training Infinite'), ('GCFF_CHALLENGE_COMBO', 'Guess Country From Flag - Challenge Combo'), ('GCFC_TRAINING_INFINITE', 'Guess Capital From Country - Training Infinite'), ('GCFC_CHALLENGE_COMBO', 'Guess Capital From Country - Challenge Combo'), ('GDFN_TRAINING_INFINITE', 'Guess Department From Number - Training Infinite'), ('GDFN_CHALLENGE_COMBO', 'Guess Department From Number - Challenge Combo')], max_length=255),
        ),
        migrations.AlterField(
            model_name='userstats',
            name='game_mode',
            field=models.CharField(choices=[('GCFF_TRAINING_INFINITE', 'Guess Country From Flag - Training Infinite'), ('GCFF_CHALLENGE_COMBO', 'Guess Country From Flag - Challenge Combo'), ('GCFC_TRAINING_INFINITE', 'Guess Capital From Country - Training Infinite'), ('GCFC_CHALLENGE_COMBO', 'Guess Capital From Country - Challenge Combo'), ('GDFN_TRAINING_INFINITE', 'Guess Department From Number - Training Infinite'), ('GDFN_CHALLENGE_COMBO', 'Guess Department From Number - Challenge Combo')], max_length=255, verbose_name='game mode'),
        ),
        migrations.AddConstraint(
            model_name='userdepartmentscore',
            constraint=models.UniqueConstraint(fields=('department', 'game_mode', 'user'), name='core_userdepartmentscore_department_game_mode_user_uniq'),
        ),
    ]