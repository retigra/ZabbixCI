# ZabbixCI Quickstart
For this tutorial, you will need to have a Zabbix server and a remote Git repository set up.
We will be making a backup of your Zabbix templates using ZabbixCI and pushing them to your Git repository.

After your templates are pushed to git, we will make changes and make sure they are pushed to git.


## Prerequisites
You will need the following things setup and working:

* A computer with a working [Python3](https://realpython.com/installing-python/) environment (can be your Zabbix Server!)
* A working [Zabbix server](https://www.zabbix.com/download)
* A [Zabbix API token](https://www.zabbix.com/documentation/7.0/en/manual/web_interface/frontend_sections/users/api_tokens)
* A remote Git repository (e.g. [Github](https://github.com) or [GitLab](https://gitlab.com))
* SSH access to Git ([Github](https://docs.github.com/en/authentication/connecting-to-github-with-ssh) | [Gitlab](https://docs.gitlab.com/ee/user/ssh.html))


## Install ZabbixCI

To install ZabbixCI, use the following command, this will install ZabbixCI and all it's dependencies:

`pip install zabbixci`

> [!IMPORTANT] 
> Some Linux distributions do not allow you to install Python packages directly via pip.
> If this is the case, you can use a Python [virtual environment](https://docs.python.org/3/tutorial/venv.html) to run ZabbixCI. 

If for some reason the installation fails with the following error:
```console
fatal error: git2.h: No such file or directory
```

Please make sure to install any [prerequisites for pygit2](https://www.pygit2.org/install.html) as well.

You should now be able to run zabbixci:
```console
user@localhost:~$ zabbixci --help
usage: zabbixci [-h] [--config CONFIG] [--zabbix-url ZABBIX_URL] [--zabbix-user ZABBIX_USER] [--zabbix-password ZABBIX_PASSWORD] [--zabbix-token ZABBIX_TOKEN] [--remote REMOTE]
                [--pull-branch PULL_BRANCH] [--push-branch PUSH_BRANCH] [--git-username GIT_USERNAME] [--git-password GIT_PASSWORD] [--git-pubkey GIT_PUBKEY] [--git-privkey GIT_PRIVKEY]
                [--git-keypassphrase GIT_KEYPASSPHRASE] [--root-template-group ROOT_TEMPLATE_GROUP] [--template-prefix-path TEMPLATE_PREFIX_PATH]
                [--template-whitelist TEMPLATE_WHITELIST] [--template-blacklist TEMPLATE_BLACKLIST] [--cache CACHE] [--dry-run] [-v] [-vv] [-vvv] [--batch-size BATCH_SIZE]
                [--ignore-template-version] [--insecure-ssl-verify] [--ca-bundle CA_BUNDLE]
                {push,pull,clearcache}

ZabbixCI is a tool to manage Zabbix templates in a Git repository. ZabbixCI adds version control to Zabbix templates, allowing you to track changes, synchronize templates between
different Zabbix servers, and collaborate with other team members.
...truncated...
user@localhost:~$
```

## Configuring ZabbixCI

ZabbixCI can be configured through commandline arguments, environment variables or a configuration file.
In this tutorial we will use a file to configure the needed parameters.

First, create a workingdir for ZabbixCI. This will be used as a local filesystem cache location as well as the location of our configuration:

```console
user@localhost:~$ mkdir zabbixci; cd zabbixci
user@localhost:~/zabbixci$
```

Now, create a `config.yaml` file with your favorite editor with the following contents (replace for your own settings).

> [!TIP] 
> You can download an [example config file](https://raw.githubusercontent.com/retigra/ZabbixCI/refs/heads/main/docs/config.yaml.example) to see all of the allowed options.

```yaml
# Zabbix API connection parameters
zabbix_token: your_Zabbix_API_token
zabbix_url: http://your.zabbix.server

# optional, if you are using untrusted certificates for Zabbix
#ignore_ssl_verify: true

# Primary Template group in Zabbix
root_template_group: Templates

# Git connection parameters
remote: git@github.com:gituser/gitrepo.git
git_pubkey: /path/to/your/ssh_pub.key
git_privkey: /path/to/your/ssh_priv.key

# optional, if you've used a passphrase on your SSH key
#git_keypassphrase: YOURPASSPHRASE
```
> [!TIP] 
> If you've loaded in your ssh key via ssh-agent, you don't need to supply the ssh parameters in the config file.

## Pushing your templates to Git

If everything is configured, we should now be able to perform a dry-run to see if everything is working as expected:

```console
user@localhost:~/zabbixci$ zabbixci push -v --config ./config.yaml --dry-run
2025-01-10 14:28:30,046 [zabbixci.zabbixci]  [INFO]: Using SSH keypair for authentication
2025-01-10 14:28:34,785 [zabbixci.utils.git.git]  [INFO]: Already up to date
2025-01-10 14:28:35,380 [zabbixci.zabbixci]  [INFO]: Found 281 templates in Zabbix
2025-01-10 14:28:35,380 [zabbixci.zabbixci]  [INFO]: Processing export batch 1/6 [1/281]
2025-01-10 14:28:55,850 [zabbixci.zabbixci]  [INFO]: Processing export batch 2/6 [51/281]
2025-01-10 14:29:15,303 [zabbixci.zabbixci]  [INFO]: Processing export batch 3/6 [101/281]
2025-01-10 14:29:34,956 [zabbixci.zabbixci]  [INFO]: Processing export batch 4/6 [151/281]
2025-01-10 14:29:53,351 [zabbixci.zabbixci]  [INFO]: Processing export batch 5/6 [201/281]
2025-01-10 14:30:12,140 [zabbixci.zabbixci]  [INFO]: Processing export batch 6/6 [251/281]
2025-01-10 14:30:25,383 [zabbixci.zabbixci]  [INFO]: Remote differs from local state, preparing to push
2025-01-10 14:30:25,682 [zabbixci.zabbixci]  [INFO]: Staged changes from your.zabbix.server committed to main
user@localhost:~/zabbixci$
```
If we don't see any errors, we can run the actual push with:
`zabbixci push -v --config ./config.yaml`

Now, your templates should show up in your Git repository!
![image](pics/git_repo_filled.png)

## Make a change

So, now we want to make a change to one of the templates in Zabbix and push this to the development branch in Git.

First, add the following line to the config.yaml file:
```yaml
push_branch: develop
```

> [!TIP] 
> We recommend using a development branch to develop and maintain templates within Git.
> Once the templates have been tested properly, you can merge the changes back to your main branch.
> See ['Branches in a nutshell'](https://git-scm.com/book/en/v2/Git-Branching-Branches-in-a-Nutshell) on working with git Branches.

Now, make a minor change to one of your Templates. In my case I added some text to the `description` field of the
template `HP iLO by SNMP`.
Rerun the command `zabbixci push -v --config ./config.yaml`:

```console
2025-01-10 15:09:34,052 [zabbixci.zabbixci]  [INFO]: Using SSH keypair for authentication
2025-01-10 15:09:37,710 [zabbixci.zabbixci]  [INFO]: Remote branch does not exist, using state from branch main
2025-01-10 15:09:39,410 [zabbixci.utils.git.git]  [INFO]: Already up to date
2025-01-10 15:09:40,274 [zabbixci.zabbixci]  [INFO]: Found 281 templates in Zabbix
2025-01-10 15:09:40,274 [zabbixci.zabbixci]  [INFO]: Processing export batch 1/6 [1/281]
2025-01-10 15:09:59,782 [zabbixci.zabbixci]  [INFO]: Processing export batch 2/6 [51/281]
2025-01-10 15:10:18,896 [zabbixci.zabbixci]  [INFO]: Processing export batch 3/6 [101/281]
2025-01-10 15:10:39,386 [zabbixci.zabbixci]  [INFO]: Processing export batch 4/6 [151/281]
2025-01-10 15:10:58,650 [zabbixci.zabbixci]  [INFO]: Processing export batch 5/6 [201/281]
2025-01-10 15:11:18,174 [zabbixci.zabbixci]  [INFO]: Processing export batch 6/6 [251/281]
2025-01-10 15:11:30,626 [zabbixci.zabbixci]  [INFO]: Remote differs from local state, preparing to push
2025-01-10 15:11:31,060 [zabbixci.zabbixci]  [INFO]: Staged changes from your.zabbix.server committed to develop
```

As you can see, some changes were detected and pushed to the `develop` branch.
You can see the diff in Git:
![image](pics/hp_ilo_change.png)


