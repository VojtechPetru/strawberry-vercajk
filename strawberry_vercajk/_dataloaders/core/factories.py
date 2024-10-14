import abc
import typing

import strawberry

if typing.TYPE_CHECKING:
    from strawberry_vercajk._dataloaders import BaseDataLoader


class BaseDataLoaderFactory[T: "BaseDataLoader"]:
    loader_class: typing.ClassVar[type[T]]
    registered_dataloaders: typing.ClassVar[dict[typing.Hashable, type[T]]] = {}

    @classmethod
    def make(cls, *, ephemeral: bool = False, **class_vars) -> type[T]:
        """
        Generates dataloader classes at runtime when they are used the first time, later gets them from cache.
        :param class_vars: kwargs passed to the dataloader class constructor
        """
        dataloader_name = cls.get_loader_unique_key(**class_vars)
        if ephemeral:
            return cls._create_dataloader_cls(dataloader_name, **class_vars)

        if dataloader_name not in cls.registered_dataloaders:
            cls.registered_dataloaders[dataloader_name] = cls._create_dataloader_cls(dataloader_name, **class_vars)
        return cls.registered_dataloaders[dataloader_name]

    @classmethod
    def _create_dataloader_cls(cls, name: str, **class_vars: type) -> type[T]:
        return typing.cast(
            type[T],
            type(
                name,
                (cls.loader_class,),
                {"Config": class_vars},
            ),
        )

    @classmethod
    def get_loader_unique_key(cls, **kwargs) -> str:
        """Return a *unique* name for the dataloader class."""
        name: str = ""
        for k, v in kwargs.items():
            if v is None:
                continue
            if isinstance(v, type):
                name += f"{k}={v.__name__}"
            else:
                name += f"{k}={v}"
        return f"{cls.loader_class.__name__}{name}"

    @classmethod
    @abc.abstractmethod
    def as_resolver(cls, *args, **kwargs) -> typing.Callable[[typing.Any, strawberry.Info], typing.Any]:
        """
        Return a dataloader as callable to be used in the field definition as a resolver.

        Example:
        -------
            @strawberry.django.type(models.User)
            class UserType:
                favourite_fruit = strawberry.django.field(resolver=<Factory>.as_resolver(args, kwargs))

        """
        raise NotImplementedError  # pragma: nocover
