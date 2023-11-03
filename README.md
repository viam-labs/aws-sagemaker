# aws-sagemaker

Viam provides an `aws-sagemaker` model of [vision service](/services/vision) with which you can use ML models you deploy on cloud endpoints using [AWS Sagemaker](https://aws.amazon.com/sagemaker/).

Configure this vision service as a [modular resource](https://docs.viam.com/modular-resources/) on your robot to access and perform inference with AWS-deployed ML models.

## Getting started

The first step is to deploy your model to the AWS Sagemaker endpoint. You can do this programmatically or through the AWS console. Instructions [here](https://docs.aws.amazon.com/sagemaker/latest/dg/deploy-model.html).

> [!NOTE]  
> Before configuring your vision service, you must [create a robot](https://docs.viam.com/manage/fleet/robots/#add-a-new-robot).

## Configuration

Navigate to the **Config** tab of your robot’s page in [the Viam app](https://app.viam.com/). Click on the **Services** subtab and click **Create service**. Select the `vision` type, then select the `aws-sagemaker` model. Enter a name for your service and click **Create**.

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

> [!NOTE]  
> For more information, see [Configure a Robot](https://docs.viam.com/manage/configuration/).

### Attributes

The following attributes are available for `viam:vision:aws-sagemaker` vision services:

| Name | Type | Inclusion | Description |
| ---- | ---- | --------- | ----------- |
| `endpoint_name` | string | **Required** | The name of the endpoint as given by AWS. |
| `aws_region` | string | **Required** | The name of the region in AWS under which the model can be found. |
| `access_json` | string | **Required** | The on-robot location of a JSON file that contains your AWS access credentials (AWS Access Key ID and Secret Access Key). Follow [these instructions](https://www.msp360.com/resources/blog/how-to-find-your-aws-access-key-id-and-secret-access-key/) to retrieve your credentials, and reference [this example JSON file containing credentials](#example-access_json). |
| `source_cams` | array | **Required** | The name of each [camera](/components/camera) you have configured on your robot that you want to use as input for the vision service. |

### Example Access JSON

```json
{
  "access_key": "UE9S0AG9KS4F3",
  "secret_access_key": "L23LKkl0d5<M0R3S4F3"
}
```

## Next steps: use your ML-enabled vision service

Now, use the `viam:vision:aws-sagemaker` modular service to perform inference with the machine learning model deployed through AWS Sagemaker on your robot.

Configure a [transform camera](https://docs.viam.com/components/camera/transform/) to see classifications or detections appear in your robot's field of vision.

You can also use the following methods of the [vision service API](https://docs.viam.com/services/vision/#api) to programmatically get detections and classifications with your modular vision service and camera:

- [`GetDetections()`](https://docs.viam.com/services/vision/#getdetections)
- [`GetDetectionsFromCamera()`](https://docs.viam.com/services/vision/#getdetectionsfromcamera)
- [`GetClassifications()`](https://docs.viam.com/services/vision/#getclassifications)
- [`GetClassificationsFromCamera()`](https://docs.viam.com/services/vision/#getclassificationsfromcamera)
