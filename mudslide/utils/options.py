import datetime
from mudslide.utils.ansi import strip_ansi
from mudslide.utils.validatorfuncs import _TZ_DICT
from mudslide.utils import validatorfuncs
from evennia.utils.utils import crop


class BaseOption:
    """
    Abstract Class to deal with encapsulating individual Options. An Option has
    a name/key, a description to display in relevant commands and menus, and a
    default value. It saves to the owner's Attributes using its Handler's save
    category.

    Designed to be extremely overloadable as some options can be cantankerous.

    Properties:
        valid: Shortcut to the loaded VALID_HANDLER.
        validator_key (str): The key of the Validator this uses.

    """

    def __str__(self):
        return "<Option {key}: {value}>".format(key=self.key, value=crop(str(self.value), width=10))

    def __repr__(self):
        return str(self)

    def __init__(self, service, key, description, default):
        self.service = service
        self.key = key
        self.default_value = default
        self.description = description

    def get(self, connection, ignore_temporary=False):
        if self.key in connection.options and not ignore_temporary:
            return connection.options[self.key]
        if not connection.logged_in:
            return self.default_value
        acc = connection.get_account()
        return acc.get_option(self)

    def set(self, connection, value, temporary=False):
        final_value = self.validate(connection, value)
        if temporary:
            connection.options[self.key] = final_value
        else:
            self.save(connection, final_value)
        return final_value

    def save(self, connection, final_value):
        if not connection.logged_in:
            return
        serialized = self.serialize(connection, final_value)
        acc = connection.get_account()
        acc.save_option(self, serialized)

    def deserialize(self, save_data):
        """
        Perform sanity-checking on the save data as it is loaded from storage.
        This isn't the same as what validator-functions provide (those work on
        user input). For example, save data might be a timedelta or a list or
        some other object.

        Args:
            save_data: The data to check.

        Returns:
            any (any): Whatever the Option needs to track, like a string or a
                datetime. The display hook is responsible for what is actually
                displayed to user.
        """
        return save_data

    def serialize(self, value):
        """
        Serializes the save data for JSON Attribute storage.

        Returns:
            value (any): The value being serialized to JSON.

        """
        pass

    def validate(self, value, **kwargs):
        """
        Validate user input, which is presumed to be a string.

        Args:
            value (str): User input.
            account (AccountDB): The Account that is performing the validation.
                This is necessary because of other settings which may affect the
                check, such as an Account's timezone affecting how their datetime
                entries are processed.
        Returns:
            any (any): The results of the validation.
        Raises:
            ValidationError: If input value failed validation.

        """
        return validatorfuncs.text(value, option_key=self.key, **kwargs)

    def display(self, **kwargs):
        """
        Renders the Option's value as something pretty to look at.

        Keyword args:
            any (any): These are options passed by the caller to potentially
                customize display dynamically.

        Returns:
            str: How the stored value should be projected to users (e.g. a raw
                timedelta is pretty ugly).

        """
        return self.value


# Option classes


class Text(BaseOption):
    def deserialize(self, save_data):
        got_data = str(save_data)
        if not got_data:
            raise ValueError(f"{self.key} expected Text data, got '{save_data}'")
        return got_data


class Email(BaseOption):
    def validate(self, value, **kwargs):
        return validatorfuncs.email(value, option_key=self.key, **kwargs)

    def deserialize(self, save_data):
        got_data = str(save_data)
        if not got_data:
            raise ValueError(f"{self.key} expected String data, got '{save_data}'")
        return got_data


class Boolean(BaseOption):
    def validate(self, value, **kwargs):
        return validatorfuncs.boolean(value, option_key=self.key, **kwargs)

    def display(self, **kwargs):
        if self.value:
            return "1 - On/True"
        return "0 - Off/False"

    def serialize(self):
        return self.value

    def deserialize(self, save_data):
        if not isinstance(save_data, bool):
            raise ValueError(f"{self.key} expected Boolean, got '{save_data}'")
        return save_data


class Color(BaseOption):
    def validate(self, value, **kwargs):
        return validatorfuncs.color(value, option_key=self.key, **kwargs)

    def display(self, **kwargs):
        return f"{self.value} - |{self.value}this|n"

    def deserialize(self, save_data):
        if not save_data or len(strip_ansi(f"|{save_data}|n")) > 0:
            raise ValueError(f"{self.key} expected Color Code, got '{save_data}'")
        return save_data


class Timezone(BaseOption):
    def validate(self, value, **kwargs):
        return validatorfuncs.timezone(value, option_key=self.key, **kwargs)

    @property
    def default(self):
        return _TZ_DICT[self.default_value]

    def deserialize(self, save_data):
        if save_data not in _TZ_DICT:
            raise ValueError(f"{self.key} expected Timezone Data, got '{save_data}'")
        return _TZ_DICT[save_data]

    def serialize(self):
        return str(self.value_storage)


class UnsignedInteger(BaseOption):
    validator_key = "unsigned_integer"

    def validate(self, value, **kwargs):
        return validatorfuncs.unsigned_integer(value, option_key=self.key, **kwargs)

    def deserialize(self, save_data):
        if isinstance(save_data, int) and save_data >= 0:
            return save_data
        raise ValueError(f"{self.key} expected Whole Number 0+, got '{save_data}'")


class SignedInteger(BaseOption):
    def validate(self, value, **kwargs):
        return validatorfuncs.signed_integer(value, option_key=self.key, **kwargs)

    def deserialize(self, save_data):
        if isinstance(save_data, int):
            return save_data
        raise ValueError(f"{self.key} expected Whole Number, got '{save_data}'")


class PositiveInteger(BaseOption):
    def validate(self, value, **kwargs):
        return validatorfuncs.positive_integer(value, option_key=self.key, **kwargs)

    def deserialize(self, save_data):
        if isinstance(save_data, int) and save_data > 0:
            return save_data
        raise ValueError(f"{self.key} expected Whole Number 1+, got '{save_data}'")


class Duration(BaseOption):
    def validate(self, value, **kwargs):
        return validatorfuncs.duration(value, option_key=self.key, **kwargs)

    def deserialize(self, save_data):
        if isinstance(save_data, int):
            return datetime.timedelta(0, save_data, 0, 0, 0, 0, 0)
        raise ValueError(f"{self.key} expected Timedelta in seconds, got '{save_data}'")

    def serialize(self):
        return self.value_storage.seconds


class Datetime(BaseOption):
    def validate(self, value, **kwargs):
        return validatorfuncs.datetime(value, option_key=self.key, **kwargs)

    def deserialize(self, save_data):
        if isinstance(save_data, int):
            return datetime.datetime.utcfromtimestamp(save_data)
        raise ValueError(f"{self.key} expected UTC Datetime in EPOCH format, got '{save_data}'")

    def serialize(self):
        return int(self.value_storage.strftime("%s"))


class Future(Datetime):
    def validate(self, value, **kwargs):
        return validatorfuncs.future(value, option_key=self.key, **kwargs)


class Lock(Text):
    def validate(self, value, **kwargs):
        return validatorfuncs.lock(value, option_key=self.key, **kwargs)
