# ZabbixCI - Containerized Deployment

ZabbixCI provides a Docker image for containerized deployment in various
environments.

## Usage

The ZabbixCI Docker image is available on GitHub Container Registry and can be
pulled using the following command:

```bash
docker pull ghcr.io/retigra/zabbixci:latest
```

Prepare SSH or HTTPS credentials for the git repository, SSH keys can be mounted
to the container. HTTPS credentials can be passed as variables. (See
[Configuration](#configuration))

The image can be run using the following command:

```bash
docker run --rm -v $(pwd)/config.yaml:/app/config.yaml ghcr.io/retigra/zabbixci:latest --config /app/config.yaml pull -vv

# Or using environment variables
docker run --rm -e GIT_USERNAME=username -e GIT_PASSWORD=access_token -e REMOTE=https://github.com/YOUR_USER/REPO_NAME.git ghcr.io/retigra/zabbixci:latest push -vv
```

The `--rm` flag removes the container after it has finished running. The `-v`
flag mounts the current directory to the `/zabbixci` directory in the container.
The `--config` flag specifies the configuration file to use. The `pull` command

## Configuration

ZabbixCI requires parameters to be set as command line arguments, a yaml
configuration or as environment variables. See the
[example configuration file](config.yaml.example). Available parameters can be
found through `zabbixci --help`.

## Cache directory

The cache directory is used as a local copy of the git repository. In a
containerized environment, the cache directory is stored in the `/app/cache`
directory. Without persistent storage, the application could take longer to run,
caused by the need to clone the repository each time the container is started.
However, however this can mitigate some possible conflicts within the cache
directory and is therefore recommended.
