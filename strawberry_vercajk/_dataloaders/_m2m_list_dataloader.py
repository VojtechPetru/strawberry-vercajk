# import typing # TODO - reimplement in Django-specific package
# from collections import defaultdict
#
# import django.db.models
# import strawberry
# from django.db.models import F, Window
# from django.db.models.functions import DenseRank
#
# from strawberry_vercajk._app_settings import app_settings
# from strawberry_vercajk._dataloaders import core
# from strawberry_vercajk._list.django import get_django_filter_q, get_django_order_by
#
# if typing.TYPE_CHECKING:
#     from django.db.models.fields.related_descriptors import ManyToManyDescriptor
#     from django.db.models.options import Options
#     from strawberry_django.fields.field import StrawberryDjangoField
#
#     from strawberry_vercajk import FilterSet, ListInnerType, PageInput, SortInput
#
#
# __all__ = (
#     "M2MListDataLoader",
#     "M2MListDataLoaderFactory",
# )
#
#
# class M2MListDataLoaderClassKwargs(typing.TypedDict):
#     field_descriptor: "ManyToManyDescriptor"
#     query_origin: type[django.db.models.Model]
#     page: typing.NotRequired["PageInput|None"]
#     sort: typing.NotRequired["SortInput|None"]
#     filterset: typing.NotRequired["FilterSet|None"]
#
#
# class M2MListDataLoader(core.BaseDataLoader):
#     """
#     # TODO docstring
#     Base loader for M2M relationship (e.g., Workplace of a User).
#
#     EXAMPLE - load workplaces of a user:
#         1. DATALOADER DEFINITION
#         class UserWorkplacesM2MDataLoader(M2MDataLoader):
#             field_descriptor = User.workplaces
#
#         2. USAGE
#         @strawberry.django.type(models.User)
#         class UserType:
#             ...
#
#             @strawberry.field
#             def workplaces(self: "models.User", info: "Info") -> list["WorkplaceType"]:
#                 return UserWorkplacesM2MDataLoader(context=info.context).load(self.pk)
#     """
#
#     Config: typing.ClassVar[M2MListDataLoaderClassKwargs]
#
#     @classmethod
#     def get_through_model(cls) -> type[django.db.models.Model]:
#         """Returns the through model of this m2m relationship."""
#         return cls.Config["field_descriptor"].rel.through
#
#     def load_fn(self, keys: list[int]) -> list["ListInnerType[django.db.models.Model]"]:
#         """
#         :param keys: list of ids from the parent model (e.g., if we want to get workplaces of users, keys are
#          user ids)
#         """
#         import strawberry_vercajk
#
#         key_id_annot: str = "_key_id"
#         accessor_name = self.accessor_name()
#         filterset = self.Config.get("filterset")
#         page = self.Config.get("page")
#         sort = self.Config.get("sort")
#         if not page:
#             page = strawberry_vercajk.PageInput(page_number=1, page_size=app_settings.LIST.DEFAULT_PAGE_SIZE)
#
#         target_qs = (
#             self.query_target()
#             .objects.annotate(
#                 **{key_id_annot: F(f"{accessor_name}__id")},
#             )
#             .filter(
#                 **{f"{key_id_annot}__in": keys},
#             )
#             .order_by()
#         )
#
#         if filterset:
#             target_qs = target_qs.filter(get_django_filter_q(filterset.get_filter_q()))
#         if sort:
#             target_qs = target_qs.order_by(*get_django_order_by(sort))
#         if page:
#             target_qs = target_qs.annotate(
#                 rank=Window(
#                     expression=DenseRank(),
#                     partition_by=[F(key_id_annot)],
#                     order_by=get_django_order_by(sort) if sort else ["pk"],  # needs to be here, otherwise doesnt work
#                 ),
#             ).filter(
#                 rank__in=range(
#                     page.page_number,
#                     # + 2 because we need to add 1 to the page size to check if there's a next page
#                     page.page_size + 2,
#                 ),
#             )
#
#         key_to_targets: dict[int, list[django.db.models.Model]] = defaultdict(list)
#         for target in target_qs:
#             key_to_targets[getattr(target, key_id_annot)].append(target)
#
#         key_to_list_type: dict[int, ListInnerType[django.db.models.Model]] = {}
#         for key in keys:
#             items = key_to_targets.get(key, [])
#             items_count = len(items)
#             if items_count > page.page_size:
#                 items = items[: page.page_size]  # we're getting 1 extra item to check if there's a next page
#             key_to_list_type[key] = strawberry_vercajk.ListInnerType(
#                 items=items,
#                 pagination=strawberry_vercajk.PageInnerMetadataType(
#                     current_page=page.page_number,
#                     page_size=page.page_size,
#                     items_count=items_count - 1 if items_count > page.page_size else items_count,
#                     has_next_page=items_count > page.page_size,
#                     has_previous_page=page.page_number > 1,
#                 ),
#             )
#         return [key_to_list_type.get(key, []) for key in keys]
#
#     @classmethod
#     def query_target(cls) -> type[django.db.models.Model]:
#         field: django.db.models.ManyToManyField = cls.Config["field_descriptor"].field
#         model_query_origin = cls.Config["query_origin"]
#         return field.model if model_query_origin == field.related_model else field.related_model
#
#     @classmethod
#     def accessor_name(cls) -> str:
#         descriptor = cls.Config["field_descriptor"]
#         query_origin = cls.Config["query_origin"]
#         field: django.db.models.ManyToManyField = descriptor.field
#         return field.attname if query_origin == field.related_model else descriptor.rel.accessor_name
#
#
# class M2MListDataLoaderFactory(core.BaseDataLoaderFactory[M2MListDataLoader]):
#     """
#     Base factory for M2M relationship dataloaders.
#     For example, get Workplaces of a User.
#
#     Example:
#     -------
#         CONSIDER DJANGO MODELS:
#             class User(models.Model):
#                 workplaces = models.ManyToManyField("Workplace", related_name="users")
#
#             class Workplace(models.Model):
#                 ...
#
#         THE FACTORY WOULD BE USED IN A FOLLOWING MANNER:
#             @strawberry.django.type(models.User)
#             class UserType:
#                 ...
#                 @strawberry.field
#                 async def workplaces(self: "models.User", info: "Info") -> list["WorkplaceType"]:
#                     loader = M2MDataLoaderFactory.make(User.workplaces)
#                     return loader(context=info.context).load(self.pk)
#
#     """
#
#     loader_class = M2MListDataLoader
#
#     @classmethod
#     def make(
#         cls,
#         *,
#         config: M2MListDataLoaderClassKwargs,
#         _ephemeral: bool = False,
#     ) -> type[M2MListDataLoader]:
#         return super().make(
#             config=config,
#             # We can't cache the dataloader class, since its "too specific" (for example, each filter value means
#             # different dataloader) and we could end up with possibly "infinite" number of classes in the memory.
#             _ephemeral=True,
#         )
#
#     @classmethod
#     def generate_loader_name(cls, config: M2MListDataLoaderClassKwargs) -> str:
#         field: django.db.models.ManyToManyField = config["field_descriptor"].field
#         model: type[django.db.models.Model] = field.model
#         meta: Options = model._meta
#         name = (
#             f"{config["query_origin"].__name__}{meta.app_label.capitalize()}{meta.object_name}"
#             f"{field.attname.capitalize()}{cls.loader_class.__name__}"
#         )
#         if config.get("page"):
#             name += "Paginated"
#         if config.get("sort"):
#             name += "Sorted"
#         if config.get("filterset"):
#             name += "Filtered"
#         return name
#
#     @classmethod
#     def as_resolver(cls) -> typing.Callable[[typing.Any, strawberry.Info], typing.Any]:
#         # the first arg needs to be called 'root'
#         def resolver(
#             root: "django.db.models.Model",
#             info: "strawberry.Info",
#             page: "PageInput|None" = strawberry.UNSET,
#             sort: "SortInput|None" = strawberry.UNSET,
#             filterset: "FilterSet|None" = strawberry.UNSET,
#         ) -> typing.Any:
#             field_data: StrawberryDjangoField = info._field
#             model: type[django.db.models.Model] = root._meta.model
#             field_descriptor: ManyToManyDescriptor = getattr(model, field_data.django_name)
#             return cls.make(
#                 config={
#                     "field_descriptor": field_descriptor,
#                     "query_origin": model,
#                     "page": page,
#                     "sort": sort,
#                     "filterset": filterset,
#                 },
#             )(info=info).load(root.pk)
#
#         return resolver
