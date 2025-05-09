from django.db import models


class Guess(models.Model):
    created_at = models.DateTimeField(db_index=True, auto_now_add=True)
    is_correct = models.BooleanField()

    class Meta:
        ordering = ("created_at",)
        verbose_name_plural = "guesses"

    def __str__(self):
        return f"{self.is_correct} on {str(self.created_at)}"

    def weight(self):
        pass
