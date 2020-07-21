from django.db import models
from django.contrib.auth.models import AbstractUser


class Host(models.Model):
    """
    Model meant to store an IP address and match it with a reverse DNS lookup.
    """
    ip = models.GenericIPAddressField(unique=True)
    name = models.TextField(null=True)


class EntityType(models.Model):
    """
    Maps with ENTITY_CLASSES in settings.
    """
    name = models.CharField(max_length=100, null=False, blank=False, unique=True)


class Entity(models.Model):
    """
    The shared ID space for all Entities such as Accounts, Games, and Channels.
    """
    entity_type = models.ForeignKey(EntityType, related_name='entities', on_delete=models.PROTECT)
    date_created = models.DateTimeField(null=False)
    name = models.CharField(max_length=255, null=False, blank=False)
    iname = models.CharField(max_length=255, null=False, blank=False)

    class Meta:
        unique_together = (('entity_type', 'iname'))


class BanEntry(models.Model):
    """
    Tracks Account bans. These remain in the system even after the ban expires,
    so admin can use them to see who's been naughty in the past.
    """
    entity = models.ForeignKey(Entity, related_name='ban_entries', on_delete=models.CASCADE)
    date_created = models.DateTimeField(null=False)
    date_expires = models.DateTimeField(null=False)
    set_by = models.ForeignKey(Entity, related_name='+', on_delete=models.PROTECT)
    notes = models.TextField(null=True, blank=False)


class Account(AbstractUser):
    """
    Django User with some modifications.
    """
    id = models.OneToOneField(Entity, primary_key=True, on_delete=models.PROTECT)
    banned = models.ForeignKey(BanEntry, related_name='active', null=True, on_delete=models.PROTECT)
    total_playtime = models.DurationField(null=False)


class LoginRecord(models.Model):
    """
    Login records are stored here - every use of 'connect'.
    This should probably only go back so far though lest the table become huge.
    """
    entity = models.ForeignKey(Entity, related_name='logins', on_delete=models.CASCADE)
    protocol = models.CharField(max_length=80, null=False, blank=False)
    server = models.CharField(max_length=80, null=False, blank=False)
    host = models.ForeignKey(Host, related_name='logins', on_delete=models.PROTECT)
    success = models.BooleanField(null=False)
    date_created = models.DateTimeField(null=False)


class GameEntry(models.Model):
    """
    All Games have an owner and a unique identifier per their owner. This might be
    'main' or 'dev' or 'special' or whatever.
    """
    entity = models.OneToOneField(Entity, primary_key=True, on_delete=models.CASCADE)
    owner = models.ForeignKey(Entity, related_name='owned_games', on_delete=models.PROTECT)
    game_key = models.CharField(max_length=255, null=False)

    class Meta:
        unique_together = (('owner', 'game_key'),)


class Player(models.Model):
    """
    Players are a unique combination of an Account and a Game. Players can adopt a different
    apparent username, or 'handle', for their participation in a given game. All Players
    are also given a unique UUID for their participation in this game that will be used
    for the Game to refer to them - thus, the Entity ID/Account ID is never exposed
    to a game database. Only Honahlee knows who is really who.
    """
    entity = models.OneToOneField(Entity, related_name='player_component', on_delete=models.CASCADE, primary_key=True)
    account = models.ForeignKey(Entity, related_name='player_entries', on_delete=models.CASCADE)
    game = models.ForeignKey(Entity, related_name='players', on_delete=models.CASCADE)
    uuid = models.UUIDField(null=False, unique=True)
    date_created = models.DateTimeField(null=False)
    handle = models.CharField(max_length=255, blank=False, null=True)
    ihandle = models.CharField(max_length=255, blank=False, null=True)

    class Meta:
        unique_together = (('account', 'game'), ('game', 'ihandle'))


class Attribute(models.Model):
    """
    All Entities can store an vast amount of categorized-and-named JSON text sections. This is used for storing
    arbitrary data on Honahlee.
    """
    entity = models.ForeignKey(Entity, related_name='attributes', on_delete=models.CASCADE)
    date_created = models.DateTimeField(null=False)
    category = models.CharField(max_length=80, null=False, blank=True)
    name = models.CharField(max_length=80, blank=False, null=False)
    value = models.JSONField()

    class Meta:
        unique_together = (('entity', 'category', 'name'),)


class ACLPermission(models.Model):
    """

    """
    name = models.CharField(max_length=50, null=False, blank=False, unique=True)


class ACLEntry(models.Model):
    """
    Access Control List entries. All Entities define Access Permissions in their Entity Class properties,
    and these can be granted/explicitly denied to those in this list. 'Deny' takes precedence over allows.
    """
    resource = models.ForeignKey(Entity, related_name='acl_entries', on_delete=models.CASCADE)
    grantee = models.ForeignKey(Entity, related_name='acl_references', on_delete=models.CASCADE)
    mode = models.CharField(max_length=30, null=False, blank=True, default='')
    deny = models.BooleanField(null=False, default=False)
    permissions = models.ManyToManyField(ACLPermission, related_name='entries')

    class Meta:
        unique_together = (('resource', 'grantee', 'mode', 'deny'),)
        index_together = (('resource', 'deny'),)
