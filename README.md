# aws-sagemaker
A module providing a model of the Viam vision service that allows you to access vision ML models deployed on cloud endpoints using AWS Sagemaker.

## Getting started

The first step is to deploy your model to the AWS Sagemaker endpoint. You can do this programmatically or through the AWS console. Instructions [here](https://docs.aws.amazon.com/sagemaker/latest/dg/deploy-model.html).

This module implements the following methods of the [vision service API](https://docs.viam.com/services/vision/#api):
  * `GetDetections()`
  * `GetDetectionsFromCamera()`
  * `GetClassifications()`
  * `GetClassificationsFromCamera()`


## Configuration
### Example Configuration

```json
{
  "modules": [
    {
      "type": "registry",
      "name": "viam_aws-sagemaker",
      "module_id": "viam:aws-sagemaker",
      "version": "0.0.1"
    }
  ],
  "services": [
    {
      "name": "myVisionModule",
      "type": "vision",
      "namespace": "rdk",
      "model": "viam:vision:aws-sagemaker",
      "attributes": {
        "access_json": "/Users/myname/Documents/accessfile.json",
        "endpoint_name": "jumpstart-dft-tf-ic-efficientnet-b1-classification-1",
        "aws_region": "us-east-2",
        "source_cams": [
          "myCam1",
          "myCam2"
        ]
      }
    }
  ]
}

```

### Module Attributes
The module has a handful of associated attributes that are important for configuration. Namely:

  * __endpoint_name__ _(string)_ - The name of the endpoint as given by AWS
  * __aws_region__ _(string)_ - The name of the region is AWS under which the model can be found
  * __access_json__ _(string)_ - The on-robot location of a JSON file that contains AWS access credentials (see below)
  * __source_cams__ _(list of strings)_ - The names of the camera(s) that may be used as input


### Example Access JSON

```json
{
  "access_key": "UE9S0AG9KS4F3",
  "secret_access_key": "L23LKkl0d5<M0R3S4F3"
}
```
