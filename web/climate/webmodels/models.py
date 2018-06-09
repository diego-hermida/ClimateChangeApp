from django.db import models

from utilities.postgres_util import import_psycopg2

# This is required to work with PyPy.
import_psycopg2()


class LikeCount(models.Model):
    id = models.SmallIntegerField(default=0, primary_key=True)
    counter = models.BigIntegerField(default=0, null=False)

    @staticmethod
    def increment_atomic(pk=0) -> bool:
        return True if LikeCount.objects.filter(pk=pk).update(counter=models.F('counter') + 1) == 1 else False

    def __str__(self):
        return 'Current number of Likes: %d' % self.counter


class ContactMessage(models.Model):
    email = models.EmailField(max_length=65)
    name = models.CharField(max_length=45)
    subject = models.CharField(max_length=55)
    message = models.CharField(max_length=1005)
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    replied = models.BooleanField(default=False, db_index=True)
    dismissed = models.BooleanField(default=False, db_index=True)

    class Meta:
        indexes = [models.Index(fields=['replied', 'dismissed'])]

    def __str__(self):
        return 'ContactMessage [email: %s, name: %s, subject: %s, message: %s, created: %s, modified: %s, ' \
               'replied: %s, dismissed: %s]' % (
                   self.email, self.name, self.subject, self.message, self.created, self.last_modified, self.replied,
                   self.dismissed)
