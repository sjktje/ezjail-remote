import sys
from os import path
from datetime import datetime

from fabric.api import run, sudo, put, env, settings
from fabric.state import output
from fabric.contrib.files import upload_template

EZJAIL_JAILDIR = '/usr/jails'
EZJAIL_RC = '/usr/local/etc/rc.d/ezjail.sh'

env['shell'] = '/bin/sh -c'
output['running'] = False


def jls():
    run('jls')

def create(name, 
    ip,
    admin=None,
    keyfile=None, 
    flavour=u'basic'):

    if admin is None:
        admin = env['local_user']
    
    if keyfile is None:
        keyfile = path.expanduser("~/.ssh/identity.pub")

    if not path.exists(keyfile):
        sys.exit("No such keyfile '%s'" % keyfile)

    print("name: %s, ip: %s, flavour: %s" % (name, ip, flavour))
    local_flavour_path = path.abspath(path.join('flavours', flavour))
    if not path.exists(local_flavour_path):
        sys.exit("No such flavour '%s'" % local_flavour_path)

    with settings(warn_only=True):
        tmp_flavour = '%s-%s' % (flavour, datetime.now().strftime('%Y%m%d%H%M%s'))
        remote_flavour_path = path.join(EZJAIL_JAILDIR, 'flavours', tmp_flavour)
        sudo("mkdir %s" % remote_flavour_path)
        sudo("chown %s %s" % (env['user'], remote_flavour_path))
        put("%s/*" % local_flavour_path, remote_flavour_path)
        upload_template(path.join(local_flavour_path, 'ezjail.flavour'),
            path.join(remote_flavour_path, 'ezjail.flavour'),
            context=locals(), backup=False)

        # create the jail using the uploaded flavour
        create_jail = sudo("ezjail-admin create -f %s %s %s" % (tmp_flavour, name, ip))
        if create_jail.succeeded:
            jail_path = path.join(EZJAIL_JAILDIR, name)
            # copy resolv.conf from host
            sudo("cp /etc/resolv.conf %s" % path.join(jail_path, 'etc', 'resolv.conf'))
            # copy the key file into flavour
            ssh_config = path.join(jail_path, 'home', admin, '.ssh')
            sudo("mkdir -p %s" % ssh_config)
            remote_keyfile = path.join(ssh_config, 'authorized_keys')
            put(keyfile, remote_keyfile, use_sudo=True)
            sudo("chown -R %s %s" % (admin, ssh_config))
            # start up the jail:
            sudo("%s start %s" % (EZJAIL_RC, name))
        sudo("rm -rf %s" % remote_flavour_path)
