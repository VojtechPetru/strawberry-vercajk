# __all__ = [
#     "BaseDataLoaderFactory",
# ]
# import abc
# import typing
#
# import strawberry
#
# from strawberry_vercajk._dataloaders.core import get_loader_unique_key
#
# if typing.TYPE_CHECKING:
#     from strawberry_vercajk._dataloaders import BaseDataLoader


# class BaseDataLoaderFactory[T: "BaseDataLoader"]:  # TODO - reimplement in Django-specific package
#     loader_class: typing.ClassVar[type[T]]
#     registered_dataloaders: typing.ClassVar[dict[typing.Hashable, type[T]]] = {}
#
#     @classmethod
#     def make(cls, *, _ephemeral: bool = False) -> type[T]:  # TODO remove config
#         """
#         Generates dataloader classes at runtime when they are used the first time, later gets them from cache.
#         :param config: kwargs passed to the dataloader class constructor
#         :param _ephemeral: If True, the dataloader class will not be cached in memory and is created each time.
#         """
#         dataloader_name = cls.generate_loader_name(config)
#         if _ephemeral:
#             return cls._create_dataloader_cls(dataloader_name, **config)
#
#         loader_key = cls.get_loader_unique_key(config)
#         if loader_key not in cls.registered_dataloaders:
#             cls.registered_dataloaders[loader_key] = cls._create_dataloader_cls(dataloader_name, **config)
#         return cls.registered_dataloaders[loader_key]
#
#     @classmethod
#     def _create_dataloader_cls(cls, name: str, **class_vars: type) -> type[T]:
#         return typing.cast(
#             type[T],
#             type(
#                 name,
#                 (cls.loader_class,),
#                 {"Config": class_vars},
#             ),
#         )
#
#     @classmethod
#     def get_loader_unique_key(cls, config: dict[str, ...]) -> int:
#         """Return a *unique* name for the dataloader class."""
#         return get_loader_unique_key(cls.loader_class, config)
#
#     @classmethod
#     @abc.abstractmethod
#     def generate_loader_name(cls) -> str:
#         """Return a name for the dataloader."""
#         raise NotImplementedError  # pragma: nocover
#
#     @classmethod
#     @abc.abstractmethod
#     def as_resolver(cls, *args, **kwargs) -> typing.Callable[[typing.Any, strawberry.Info], typing.Any]:
#         """
#         Return a dataloader as callable to be used in the field definition as a resolver.
#
#         Example:
#         -------
#             @strawberry.django.type(models.User)
#             class UserType:
#                 favourite_fruit = strawberry.django.field(resolver=<Factory>.as_resolver(args, kwargs))
#
#         """
#         raise NotImplementedError  # pragma: nocover
