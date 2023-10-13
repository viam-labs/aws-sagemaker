import asyncio

from viam.services.vision import Vision
from viam.module.module import Module
from viam.resource.registry import Registry, ResourceCreatorRegistration
from aws_sagemaker.aws_sagemaker import AWS


async def main():
    """
    This function creates and starts a new module, after adding all desired
    resource models. Resource creators must be registered to the resource
    registry before the module adds the resource model.
    """
    Registry.register_resource_creator(
        Vision.SUBTYPE,
        AWS.MODEL,
        ResourceCreatorRegistration(AWS.new_service, AWS.validate_config))
    module = Module.from_args()

    module.add_model_from_registry(Vision.SUBTYPE, AWS.MODEL)
    await module.start()


if __name__ == "__main__":
    asyncio.run(main())