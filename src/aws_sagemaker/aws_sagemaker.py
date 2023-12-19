from io import BytesIO
from typing import ClassVar, List, Mapping, Sequence, Any, Dict, Optional, Union, cast
from typing_extensions import Self
from PIL import Image

from viam.components.camera import Camera
from viam.media.video import RawImage, CameraMimeType, ViamImage
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
    # (viam:vision:aws-sagemaker) viam = namespace, vision = family, aws-sagemaker = model name.
    MODEL: ClassVar[Model] = Model(ModelFamily("viam", "vision"), "aws-sagemaker")

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
        source_cams = config.attributes.fields["source_cams"].list_value
    
        return source_cams
    

    # Handles attribute reconfiguration
    def reconfigure(self,
                    config: ServiceConfig,
                    dependencies: Mapping[ResourceName, ResourceBase]):

        self.endpoint_name = config.attributes.fields["endpoint_name"].string_value
        self.aws_region = config.attributes.fields["aws_region"].string_value
        access_json = config.attributes.fields["access_json"].string_value
        self.source_cams = config.attributes.fields["source_cams"].list_value
        self.cameras = {} 

        # Build cam_name -> camera map
        for cam in self.source_cams:
            self.cameras[cam] = dependencies[Camera.get_resource_name(cam)]
        
        # Grab access information from json file
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

    async def get_classifications(self,
                                 image: ViamImage,
                                 count: int,
                                 *, 
                                 extra: Optional[Dict[str, Any]] = None,
                                 timeout: Optional[float] = None,
                                 **kwargs) -> List[Classification]:
        classifications = []
        img = image.image
        if isinstance(img, RawImage):
            if img.mime_type in [CameraMimeType.JPEG, CameraMimeType.PNG]:
                response = self.client.invoke_endpoint(EndpointName=self.endpoint_name, 
                                                   ContentType= 'application/x-image',
                                                   Accept='application/json;verbose',
                                                   Body=img.data) 
            else:
                raise Exception("Image mime type must be JPEG or PNG, not ", img.mime_type)

        else:
            stream = BytesIO()
            img = img.convert("RGB")
            img.save(stream, "JPEG")
            response = self.client.invoke_endpoint(EndpointName=self.endpoint_name, 
                                                   ContentType= 'application/x-image',
                                                   Accept='application/json;verbose',
                                                   Body=stream.getvalue())
            
        # Package results based on standardized output 
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
        if camera_name not in self.source_cams:
            raise Exception(
                "Camera name given to method",camera_name, " is not one of the configured source_cams ", self.source_cams)
        cam = self.cameras[camera_name]
        img = await cam.get_image()
        return await self.get_classifications(image=img, count=count)
 
    async def get_detections(self,
                            image: ViamImage,
                            *,
                            extra: Optional[Dict[str, Any]] = None,
                            timeout: Optional[float] = None,
                            **kwargs) -> List[Detection]:
        
        detections = []
        img = image.image
        if isinstance(img, RawImage):
            if img.mime_type in [CameraMimeType.JPEG, CameraMimeType.PNG]:
                decoded = Image.open(BytesIO(img.data))
                width, height = decoded.width, decoded.height
                response = self.client.invoke_endpoint(EndpointName=self.endpoint_name, 
                                                   ContentType= 'application/x-image',
                                                   Accept='application/json;verbose',  
                                                   Body=img.data) 
            else:
                 raise Exception("Image mime type must be JPEG or PNG, not ", img.mime_type)

        else:
            width, height = float(img.width), float(img.height)
            stream = BytesIO()
            img = img.convert("RGB")
            img.save(stream, "JPEG")
            response = self.client.invoke_endpoint(EndpointName=self.endpoint_name, 
                                                   ContentType= 'application/x-image',
                                                   Accept='application/json;verbose',
                                                   Body=stream.getvalue())
            
        # Package results based on standardized output
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


        if camera_name not in self.source_cams:
            raise Exception(
                "Camera name given to method",camera_name, " is not one of the configured source_cams ", self.source_cams)
        cam = self.cameras[camera_name]
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
    

