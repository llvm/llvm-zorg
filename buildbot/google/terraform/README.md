This folder contains the Terraform configuration to spawn the build bots.

Before deploying anything new, use `terraform plan` to check that you're only 
modifying the parts that you intended to.


# Installation

To set up your local machine to deploy changes to the cluster follow these 
steps:

1. Install these tools:
    1. [Terraform](https://learn.hashicorp.com/terraform/getting-started/install.html)
    1. [Google Cloud SDK](https://cloud.google.com/sdk/install)
    1. [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)
1. Run `llvm-zorg/buildbot/google/gcloud_config.sh` to configure the Google
   Cloud SDK.
1. To configure the GCP credetianls for terraform run: 
   ```bash
    export GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcloud/legacy_credentials/<your email>/adc.json
    export GOOGLE_CLOUD_KEYFILE_JSON=$GOOGLE_APPLICATION_CREDENTIALS
    ```
    Note: Some documentation recommends `GOOGLE_CREDENTIALS` for this, however
    this does not work for accessing the Google Cloud Storage backend in 
    terraform. You need to set both variables, as they are required by different
    tools

# Deploying to new Google Cloud project

When deploying this cluster to a completely new Google Cloud project, these 
manual steps are required:

* You need to create the GCP project manually before Terraform works.
* You also need to go to the Kubernetes page once, to enable Kubernetes and 
  Container Registry for that project.
* GPUs need to be enabled on Kubernetes by following these
[instructions](https://cloud.google.com/kubernetes-engine/docs/how-to/gpus#installing_drivers).
* Terraform needs to share a "state" between all users. The "backend" for this
  can be a "bucket" on Google Cloud Storage. So you need to create that bucket
  and give all users write access. In addition, you should enable "object
  versioning" to be able to access previous versions of the state in case it
  gets corrupted: 
  ```bash
  gsutil versioning set on gs://<bucket name>
  ````
* Store the secrets (see next section).


# Secrets

To keep secrets a secret, they MUST not be stored in version control. The right
place on kubernetes is a "secret". To create a kubernetes secret for the agent
token: 
```bash
kubectl create secret generic buildbot-token-mlir-nvidia --from-file=token=<file name>
```
The file in `<file name>` then must contain the password of the buildbot worker
in plain text. In the `Deployment` of a container, the secret is defined as a 
special type of volume and mounted in the specified path. During runtime the 
secret can then be read from that file.

An example:
The secret `buildbot-token-mlir-nvidia` is defined (as above) in Kubernetes. 
In the [deployment](buildbot/google/terraform/main.tf) `mlir-nvidia` it is 
used as a volume of type `secret` and then mounted at `/secrets`. During the 
runtime of the docker container, the script 
[run.sh](../docker/buildbot-mlir-nvidia/run.sh) reads the secret from the file
`/secrets/token` and uses it to create the worker configuration.


# Using GPUs on Google Cloud

Terraform does not support deployments on GCP using a GPU at the moment.
So we need to deploy such cases using plain Kubernetes configuration files.
See this [issue](https://github.com/terraform-providers/terraform-provider-kubernetes/issues/149) 
for more details.
The buildbot mlir-nvidia is configured in `deployment-mlir-nvidia.yaml` in this
folder. 

For all non-GPU cases add a `"kubernetes_deployment"` to `main.tf`. 
The contents is identical to the the Kubernetes file, just the markup is 
different.

Kubernetes files are also declarative, so you can re-deploy them when you made
a change. They can be deployed with:
```bash
kubectl apply -f myfile.yaml
```
