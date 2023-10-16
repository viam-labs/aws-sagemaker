from io import BytesIO
from typing import ClassVar, List, Mapping, Sequence, Any, Dict, Optional, Union, cast

from typing_extensions import Self
from PIL import Image

from viam.components.camera import Camera
from viam.media.video import RawImage, CameraMimeType
from viam.proto.service.vision import Classification, Detection
from viam.services.vision import Vision
from viam.module.types import Reconfigurable
from viam.proto.app.robot import ServiceConfig
from viam.proto.common import PointCloudObject, ResourceName
from viam.resource.base import ResourceBase
from viam.resource.types import Model, ModelFamily
from viam.utils import ValueTypes

import boto3
import json


class AWS(Vision, Reconfigurable):
    """
    AWS implements a vision service that only supports detections
    and classifications.

    It inherits from the built-in resource subtype Vision and conforms to the
    ``Reconfigurable`` protocol, which signifies that this component can be
    reconfigured. Additionally, it specifies a constructor function
    ``AWS.new_service`` which confirms to the
    ``resource.types.ResourceCreator`` type required for all models.
    """

    # Here is where we define our new model's colon-delimited-triplet
    # (acme:demo:mybase) viam = namespace, demo = family, mybase = model name.
    MODEL: ClassVar[Model] = Model(ModelFamily("viam", "vision"), "aws-sagemaker")

    # Put more class variables here if/when we need them
    def __init__(self, name: str):
        super().__init__(name=name)

    # Constructor
    @classmethod
    def new_service(cls,
                 config: ServiceConfig,
                 dependencies: Mapping[ResourceName, ResourceBase]) -> Self:
        service = cls(config.name)
        service.reconfigure(config, dependencies)
        return service

    # Validates JSON Configuration
    @classmethod
    def validate_config(cls, config: ServiceConfig) -> Sequence[str]:
        endpoint_name = config.attributes.fields["endpoint_name"].string_value
        if endpoint_name == "":
            raise Exception(
                "An endpoint name is required as an attribute for an AWS vision service.")
        aws_region = config.attributes.fields["aws_region"].string_value
        if aws_region == "":
            raise Exception(
                "The AWS region is required as an attribute for an AWS vision service.")
        access_json = config.attributes.fields["access_json"].string_value
        if access_json == "":
            raise Exception(
                "The location of the access JSON file is required as an attribute for an AWS vision service.")
        if access_json[-5:] != ".json":
            raise Exception(
                "The location of the access JSON must end in '.json'")
        camera_name = config.attributes.fields["camera_name"].string_value
        if camera_name == "":
            return
        
        return [camera_name]


    # Handles attribute reconfiguration
    def reconfigure(self,
                    config: ServiceConfig,
                    dependencies: Mapping[ResourceName, ResourceBase]):

        self.endpoint_name = config.attributes.fields["endpoint_name"].string_value
        self.aws_region = config.attributes.fields["aws_region"].string_value
        access_json = config.attributes.fields["access_json"].string_value
        camera_name = config.attributes.fields["camera_name"].string_value
        if camera_name != "":
            self.camera_name = camera_name
            self.camera = dependencies[Camera.get_resource_name(camera_name)]
        
        with open(access_json, 'r') as f:
            accessStuff = json.load(f)
            self.access_key = accessStuff['access_key']
            self.secret_key = accessStuff['secret_access_key']

        # Set up sagemaker client on reconfigure
        self.client = boto3.client('sagemaker-runtime', region_name=self.aws_region,
                        aws_access_key_id= self.access_key,
                         aws_secret_access_key = self.secret_key)

    """
    Implement the methods the Viam RDK defines for the vision service API
    (rdk:service:vision)
    """

    # Tested with 3 detection and 3 classification models and went well.
    # The problem is that detection models are slow AT THE ENDPOINT NOT MY DOING
    # But it seems you can "Accept" different response types and that makes a time diff

    async def get_classifications(self,
                                 image: Union[Image.Image, RawImage],
                                 count: int,
                                 *, 
                                 extra: Optional[Dict[str, Any]] = None,
                                 timeout: Optional[float] = None,
                                 **kwargs) -> List[Classification]:
        classifications = []
        if isinstance(image, RawImage):
            response = self.client.invoke_endpoint(EndpointName=self.endpoint_name, 
                                                   ContentType= 'application/x-image',
                                                   Accept='application/json;verbose',
                                                   Body=image.data) # send image.data[24:]??
        else:
            stream = BytesIO()
            image = image.convert("RGB")
            image.save(stream, "JPEG")
            response = self.client.invoke_endpoint(EndpointName=self.endpoint_name, 
                                                   ContentType= 'application/x-image',
                                                   Accept='application/json;verbose',
                                                   Body=stream.getvalue())
            
        # Either way... 
        out = json.loads(response['Body'].read())
        labels = out['labels']
        probs = out['probabilities']
        zipped = list(zip(labels, probs)) 
        res = sorted(zipped, key = lambda x: -x[1]) # zipped in decreasing probability order
        for i in range(count):
            classifications.append({"class_name": res[i][0], "confidence": res[i][1]})

        return classifications
    

    async def get_classifications_from_camera(self, 
                                              camera_name: str, 
                                              count: int, 
                                              *,
                                              extra: Optional[Dict[str, Any]] = None,
                                              timeout: Optional[float] = None,
                                              **kwargs) -> List[Classification]:
        if camera_name != self.camera_name:
            raise Exception(
                "Camera name given to method",camera_name, " is not the one given to configuration ",self.camera_name)
        cam = self.camera
        img = await cam.get_image()
        return await self.get_classifications(image=img, count=count)

    
    async def get_detections(self,
                            image: Union[Image.Image, RawImage],
                            *,
                            extra: Optional[Dict[str, Any]] = None,
                            timeout: Optional[float] = None,
                            **kwargs) -> List[Detection]:
        
        detections = []
        if isinstance(image, RawImage):
            width, height = int.from_bytes(image.data[8:16], "big"), int.from_bytes(image.data[16:24], "big")
            response = self.client.invoke_endpoint(EndpointName=self.endpoint_name, 
                                                   ContentType= 'application/x-image',
                                                   Accept='application/json;verbose',  # be less verbose?
                                                   Body=image.data) # send image.data[24:]??
        else:
            width, height = float(image.width), float(image.height)
            stream = BytesIO()
            image = image.convert("RGB")
            image.save(stream, "JPEG")
            response = self.client.invoke_endpoint(EndpointName=self.endpoint_name, 
                                                   ContentType= 'application/x-image',
                                                   Accept='application/json;verbose',
                                                   Body=stream.getvalue())
            
        # Either way... 
        out = json.loads(response['Body'].read())
        boxes =  out['normalized_boxes']
        classes= out['classes']
        scores = out['scores']
        labels = out['labels']
        n = min(len(boxes), len(classes), len(scores))
        
        for i in range(n):
            xmin, xmax = boxes[i][0] * width, boxes[i][2] * width
            ymin, ymax = boxes[i][1] * height, boxes[i][3] * height

            detections.append({ "confidence": float(scores[i]), "class_name": str(labels[int(classes[i])]), 
                                         "x_min": int(xmin), "y_min": int(ymin), "x_max": int(xmax), "y_max": int(ymax) })

        return detections
    

    async def get_detections_from_camera(self,
                                        camera_name: str,
                                        *,
                                        extra: Optional[Dict[str, Any]] = None,
                                        timeout: Optional[float] = None,
                                        **kwargs) -> List[Detection]:
        
        if camera_name != self.camera_name:
            raise Exception(
                "Camera name given to method",camera_name, " is not the one given to configuration ",self.camera_name)
        cam = self.camera
        img = await cam.get_image()
        return await self.get_detections(image=img)
    
    
    async def get_object_point_clouds(self,
                                      camera_name: str,
                                      *,
                                      extra: Optional[Dict[str, Any]] = None,
                                      timeout: Optional[float] = None,
                                      **kwargs) -> List[PointCloudObject]:
        raise NotImplementedError
    
    async def do_command(self,
                        command: Mapping[str, ValueTypes],
                        *,
                        timeout: Optional[float] = None,
                        **kwargs):
        raise NotImplementedError
    

