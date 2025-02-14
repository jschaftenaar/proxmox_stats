## Void Metrics

### No install No configuration metrics for home clusters.

### Goals
Not having to install agents on target hosts. Just set your inventory and startup the app. That is it.

There is a simple docker-compose file as example as well as a simple k8s manifest file

### It does not have ...
- Yes it does not have extensive metrics, this is meant for a home cluster
- Yes you can add metrics for yourself by simply updating the single ansible file


### Requirements
- The statistics only work for linux based hosts currently and are fairly dumb by default, this is by design


