from django.db import models
from django.contrib.auth.models import (
    BaseUserManager, AbstractBaseUser, PermissionsMixin
)

import re

YES_NO = (
    ('Y','Yes'),
    ('N','No')
)

PROTOCOLS = (
    ('irc','IRC'),
    ('discord','Discord')
)

COLORS = (
    ('white','White'),
    ('black','Black'),
    ('darkblue','Dark Blue'),
    ('green','Green'),
    ('red','Red'),
    ('maroon','Dark Red'),
    ('purple','Purple'),
    ('orange','Orange'),
    ('yellow','Yellow'),
    ('lime','Lime'),
    ('teal','Teal'),
    ('aqua','Aquamarine'),
    ('blue','Blue'),
    ('fuchsia','Fuchsia'),
    ('gray','Gray'),
    ('silver','Silver')
)


class SmaugUserManager(BaseUserManager):

    def create_user(self, username, password=None, name=None, email=None):

        # Create the user
        if email: email = SmaugUserManager.normalize_email(email)
        user = self.model(username=username, name=name, email=email)
        if password: user.set_password(password)
        user.save(using=self._db)
        
        # Add protocol profiles
        profile = SmaugUserProfile(user=user)
        profile.save(using=self._db)
        return user

    def create_superuser(self, username, password, name=None, email=None):
        user = self.create_user(username, password, name, email)
        user.is_admin = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class SmaugUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(unique=True, max_length=64)
    name = models.CharField(null=True, blank=True, max_length=64)
    email = models.EmailField(null=True, blank=True, unique=True, max_length=255, db_index=True)
    objects = SmaugUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    def get_full_name(self):
        return self.username

    def get_short_name(self):
        return self.username

    def __unicode__(self):
        return self.username

    def has_perm(self, perm, obj=None):
        """ Does the user have a specific permission?"
        """
        return True

    def has_module_perms(self, app_label):
        """ Does the user have permissions to view the app `app_label`?
        """
        return True

    @property
    def is_staff(self):
        """ Is the user a member of staff?
        """
        return self.is_superuser
    

class SmaugUserProfile(models.Model):
    user = models.OneToOneField(SmaugUser, related_name="profile")
    proto = models.CharField(max_length=8, choices=PROTOCOLS, db_index=True)
    color = models.CharField(null=True, blank=True, max_length=16, choices=COLORS)
    info = models.CharField(null=True, blank=True, max_length=255)
    sign_on = models.DateTimeField(null=True, blank=True)
    sign_off = models.DateTimeField(null=True, blank=True)
    last_comment = models.DateTimeField(null=True, blank=True)
    access = models.IntegerField(null=True, blank=True)

    def __unicode__(self):
        return "%s's profile" % self.user

    class Meta:
        permissions = (
            ("can_view_logs", "Can view logs"),
        )

    class Admin:
        list_display = ('user','name','info','www',)


class SmaugUserHandle(models.Model):
    profile = models.ForeignKey(SmaugUserProfile, related_name="handles")
    handle = models.CharField(max_length=64, db_index=True)
    proto = models.CharField(max_length=8, choices=PROTOCOLS, db_index=True)

    def __unicode__(self):
        return self.handle

    class Admin:
        list_display = ('user','handle','proto',)


class IrcUserHost(models.Model):
    profile = models.ForeignKey(SmaugUserProfile, related_name="hosts")
    host = models.CharField(primary_key=True, max_length=64, db_index=True)

    class Admin:
        list_display = ('user','host',)


class LogLine(models.Model):
    stamp = models.DateTimeField(db_index=True)
    proto = models.CharField(max_length=8, choices=PROTOCOLS, db_index=True)
    handle = models.CharField(blank=True, null=True, max_length=64, db_index=True)
    body = models.TextField(blank=True, null=True)
    user = models.ForeignKey(SmaugUser, related_name="lines", null=True, db_index=True)
    year = models.IntegerField(blank=True, null=True, db_index=True)
    month = models.IntegerField(blank=True, null=True, db_index=True)
    external_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    edited = models.CharField(blank=True, null=True, max_length=1, choices=YES_NO, db_index=True, default='N')
    deleted = models.CharField(blank=True, null=True, max_length=1, choices=YES_NO, db_index=True, default='N')

    def __unicode__(self):
        return "<%s> %s" % (self.handle, self.body)

    class Meta:
        index_together = [
            ["year", "month"],
        ]

class Message(models.Model):
    from_user = models.ForeignKey(SmaugUser, related_name="sent")
    to_user = models.ForeignKey(SmaugUser, related_name="recieved")
    body = models.TextField(blank=True)
    passed = models.CharField(max_length=1, choices=YES_NO, default='N')
    seen = models.CharField(max_length=1, choices=YES_NO, default='N')
    stamp = models.DateTimeField(db_index=True)

    def get_summary(self):
        s = self.get_body()
        if len(s) > 20:
            s = "%s..."%s[:20]
        return s

    def get_body(self):
        s = self.body
        s = re.sub("[\x80-\xff]", "?", s)
        return s

    class Admin:
        list_display = ('date','from_user','to_user','body',)


class RpsGame(models.Model):
    winner = models.ForeignKey(SmaugUser, related_name="rps_wins")
    winner_play = models.CharField(blank=True, max_length=3)
    winner_time = models.CharField(blank=True, max_length=16)
    loser = models.ForeignKey(SmaugUser, related_name="rps_losses")
    loser_play = models.CharField(blank=True, max_length=3)
    loser_time = models.CharField(blank=True, max_length=16)
    rounds = models.IntegerField(null=True, blank=True)

    class Admin:
        list_display = ('id','winner','loser','winner_play','loser_play','rounds',)


class QuoteLink(models.Model):
    pub_date = models.DateField()
    match_text = models.TextField()
    title = models.CharField(max_length=255)
    url = models.TextField()

