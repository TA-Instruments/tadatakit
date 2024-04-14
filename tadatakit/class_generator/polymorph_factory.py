from typing import Dict

from .utils import pascal_to_snake


class PolymorphFactory:
    def __init__(self, definition_registry, definition: Dict):
        self.definition_registry = definition_registry
        self.discriminator_property = definition["discriminator"]["propertyName"]
        self.discriminator_mapping = {
            mapping_value: self.definition_registry._casters[ref.split("/")[-1]]
            for mapping_value, ref in definition["discriminator"]["mapping"].items()
        }

    def discriminate(self, **kwargs):
        return self.discriminator_mapping[kwargs[self.discriminator_property]](**kwargs)

    def from_dict(self, data_dict: Dict):
        return self.discriminator_mapping[
            data_dict[self.discriminator_property]
        ].from_dict(data_dict)
