import atexit
import subprocess
import json
import sys
import os
import socket
import shutil
import zipfile
import tarfile
import time
from os import path
from time import sleep
from getpass import getpass
from signal import SIGTERM

from splunk.util import normalizeBoolean

# We use Splunk's cli library, and we force it to never use the merged
# cached configs (it will still cache individual files). We cannot rely on 
# the merged conf files as they may be out of date (they update when Splunkweb
# starts up or other similar events). Given that, we will go to the source files.
useCachedConfigs = False
from splunk.clilib.cli_common import getConfKeyValue

MAIN_DIR = path.abspath(path.join(path.dirname(__file__), ".."))
HAS_LINK = hasattr(os, 'symlink')

SPLUNKDJ_APPSERVER_DEFAULT_PORT = 8080
SPLUNKDJ_PROXY_DEFAULT_PORT = 3000
SPLUNKDJ_PROXY_DEFAULT_PATH = "/api"
DEFAULT_SPLUNKDJ_CONFIG_FILE = ".splunkdjrc"
SPLUNK_HOME_FILE = ".splunkhome"
SPLUNKDJ_DEFAULT_APPS = ["quickstartfx", "homefx", "examplesfx", "testfx"]

is_win32 = sys.platform == "win32"

try:
    current_dir = os.path.dirname(__file__)

    # Add the contrib packages to our pythonpath
    contrib_dir = os.path.join(current_dir, '..', 'contrib')
    for contrib_package_path in os.listdir(contrib_dir):
        contrib_package_path = os.path.join(contrib_dir, contrib_package_path)
        contrib_package_path = os.path.abspath(contrib_package_path)
        sys.path.insert(0, contrib_package_path)
        
    # We have to add Django to the environment, so that forks will pick it up
    django_path = os.path.abspath(os.path.join(current_dir, '..', 'contrib', 'django'))
    os.environ['PYTHONPATH'] = '%s%s%s' % (django_path, os.pathsep, os.environ['PYTHONPATH'])
    
    import envoy
    from envoy import expand_args, ConnectedCommand
    import aaargh
    from aaargh import App
except:
    os.unlink(path.join(MAIN_DIR, SPLUNK_HOME_FILE))
    print "The location for SPLUNK_HOME ('%s') is not valid. Run 'splunkdj setup' and try again." % os.environ['SPLUNK_HOME']
    sys.exit(1)

app = App(description="Web Framework")

def grepsingle(txt, pattern):
    lines = txt.split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith(pattern):
            return line

def get_splunk_home():
    return os.environ.get("SPLUNK_HOME", "")
    
def get_apps_base():
    # Find the apps base relative to Splunk, respecting SHP/etc.
    try:
        import splunk.clilib.bundle_paths as bundle_paths
        return bundle_paths.get_base_path()
    except:
        return os.path.join(get_splunk_home(), "etc", "apps")

def get_splunk_path():
    splunk_bin_path = path.join(get_splunk_home(), "bin", "splunk" + (".exe" if is_win32 else ""))
    if not (path.exists(splunk_bin_path) and path.isfile(splunk_bin_path)):
        print "Could not find the splunk executable at '%s'.  Please check SPLUNK_HOME and try again." % splunk_bin_path
        sys.exit(1)
    return splunk_bin_path
        
def get_conf_value(conf, stanza, key):
    # This wrapper is here for future functionality
    return getConfKeyValue(conf, stanza, key)

def confirm(prompt_str="Confirm", allow_empty=True, default=False):
    fmt = (prompt_str, 'y', 'n') if default else (prompt_str, 'n', 'y')
    if allow_empty:
        prompt = '%s [%s]|%s: ' % fmt
    else:
        prompt = '%s %s|%s: ' % fmt
    
    while True:
        ans = raw_input(prompt).lower().strip()
        
        if ans == '' and allow_empty:
            return default
        elif ans in ['y', 'yes']:
            return True
        elif ans in ['n', 'no']:
            return False
        else:
            print 'Enter y or n.'

# We create a demo args object that we can fill
class Args(object):
    def __init__(self, *args, **kwargs):
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

def is_port_open(ip, port):    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:        
        s.connect((ip, int(port)))
        s.shutdown(2)
        s.close()
        return True
    except Exception, e:
        return False

def generate_random_key():
    from django.utils.crypto import get_random_string
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
    secret_key = get_random_string(50, chars)
    
    return secret_key

def check_splunk():    
    setup_django_environment()
    
    from django.conf import settings
    from splunklib.client import Service
    
    host = settings.SPLUNKD_HOST
    port = settings.SPLUNKD_PORT
    scheme = settings.SPLUNKD_SCHEME
    
    service = Service(
        token="unnecessary_token",
        scheme=scheme,
        host=host,
        port=port
    )
    
    version = [0]
    try:   
        info = service.info()
        version = map(int, info.version.split("."))
    except Exception as e:
        print "Could not connect to Splunk at %s:%s." % (host, port)
        sys.exit(1)
        
    # Make sure it is greater than Splunk 5.0, or an internal build
    if (version[0] < 5 and not version[0] > 1000):
        print "You have Splunk %s, but the Splunk Web Framework requires Splunk 5.0 or later." % info.version
        sys.exit(1)

def setup_django_environment():
    try:
        sys.path.append(path.join(MAIN_DIR, "server"));
        server_py = path.join(MAIN_DIR, "server", "manage.py")
        
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
        from django.conf import settings
        settings.SPLUNKD_PORT
    except Exception, e:
        print "There was an error setting up the Django environment:"
        print e
        sys.exit(1)
    
def run_django_command(command, args, require_settings = True):
    try:
        sys.path.append(path.join(MAIN_DIR, "server"));
        server_py = path.join(MAIN_DIR, "server", "manage.py")

        # Differentiates between those manage.py commands that require
        # a working settings.py, and those that can run without it, like 
        # startapp.
        if require_settings:
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
        
        # Prepare argv
        argv = list(args)
        argv.insert(0, command)        
        argv.insert(0, server_py)
        
        from django.core.management import ManagementUtility
        commander = ManagementUtility(argv)
        commander.execute()
    except Exception, e:
        print "There was an error running the '%s' command with '%s'." % (command, args)
        raise
        
    return
    
def connect(argv, data=None, env=None, cwd=None, stdin=None, stdout=None, stderr=None):
    """Spawns a new process from the given args."""

    environ = dict(os.environ)
    environ.update(env or {})

    process = subprocess.Popen(
        argv,
        universal_newlines=True,
        shell=False,
        env=environ,
        stdin=stdin or subprocess.PIPE,
        stdout=stdout or subprocess.PIPE,
        stderr=stderr or subprocess.PIPE,
        bufsize=0,
        cwd=cwd,
    )

    return ConnectedCommand(process=process)
    
def get_pid_file(config, name):
    pid_directory = config.get("pid_directory", path.join(os.environ.get("SPLUNK_HOME"), "var", "run", "splunk"))
    return path.join(pid_directory, "%s.pid" % name)
    
def get_django_pid_file(config):
    return get_pid_file(config, "splunk_django_wsgi_%s" % config["splunkdj_port"])
    
def get_proxy_pid_file(config):
    return get_pid_file(config, "splunk_node_proxy_%s" % config["proxy_port"])
    
def stop_django(config):
    pid_file = get_django_pid_file(config)
    server_py = path.join(MAIN_DIR, "server", "manage.py")
    argv = [config['python'], server_py, "runwsgiserver", "stop", "pidfile=%s" % pid_file]
    
    connected = connect(argv, stdout=sys.stdout, stderr=sys.stderr)
    
    def cleanup():
        try:
            connected.kill()
        except:
            # Ignore errors during cleanup
            pass
    atexit.register(cleanup)
    
    # Block until the process is killed
    connected.block()
    
def start_django(config, daemonize=False):    
    server_py = path.join(MAIN_DIR, "server", "manage.py")
    argv = [config['python'], server_py, "runwsgiserver", "autoreload=true"]
    
    if daemonize:
        stop_django(config)
        
        pid_file = get_django_pid_file(config)
            
        argv.append("daemonize=true")
        argv.append("pidfile=%s" % pid_file)
    
    connected = connect(argv, stdout=sys.stdout, stderr=sys.stderr)
    
    def cleanup():
        try:
            connected.kill()
        except:
            # Ignore errors during cleanup
            pass
    atexit.register(cleanup)
    
    return connected
    
def stop_proxy(config):
    pid_file = get_proxy_pid_file(config)
    
    # The below code is adapted from various samples
    # to get it to work for our case.
    
    # Get the pid from the pidfile
    try:
        pf = file(pid_file,'r')
        pid = int(pf.read().strip())
        pf.close()
    except IOError:
        pid = None

    # If there is no pid, then we just return
    if not pid:
        return

    # Try killing the daemon proxy    
    try:
        while True:
            os.kill(pid, SIGTERM)
            time.sleep(0.1)
    except OSError, err:
        err = str(err)
        if err.find("No such process") > 0:
            if path.exists(pid_file):
                os.remove(pid_file)
        else:
            print str(err)
            sys.exit(1)
    
def start_proxy(config, daemonize=False):
    argv = None    
    connected = None
    pid_file = get_proxy_pid_file(config)
    argv = [config['node'], path.join(MAIN_DIR, "proxy", "proxy.js")]
        
    # Get the appropriate stdin/stdout/stderr
    stdin  = None       if not daemonize else file(os.devnull, 'r')
    stdout = sys.stdout if not daemonize else file(os.devnull, 'a+')
    stderr = sys.stderr if not daemonize else file(os.devnull, 'a+', 0)
        
    connected = connect(
        argv,
        stdin=stdin,
        stdout=stdout, 
        stderr=stderr)
    
    if daemonize:
        # We already forked the process, we simply need to get the pid
        # and then write it out to the file
        pid = str(connected.pid)
        with file(pid_file, 'w+') as f:
            f.write("%s\n" % pid)
    else:
        def cleanup():
            try:
                connected.kill()
            except:
                # Ignore errors during cleanup
                pass
                
        atexit.register(cleanup)
    
    return connected

def setup_environment(configfile):
    config_file = path.join(MAIN_DIR, configfile)
    
    if not path.exists(config_file):
        print "The '%s' configuration file doesn't exist. Run 'splunkdj setup' and try again." % config_file
        sys.exit(1)
    
    config = None
    try:
        config = json.load(open(config_file, 'r'))
    except:
        print "There was an error parsing '%s'. Run 'splunkdj setup' and try again." % config_file
        sys.exit(1)
    
    os.environ['SPLUNKDJ_CONFIG'] = config_file
        
    return config
    
def try_import(libs):
    imports = 0
    for lib in libs:
        try:
            __import__(lib)
            imports += 1
        except:
            pass
    
    return imports > 0

# When we install a new app, we need a way to refresh the conf files
# so that everything is picked up
def refresh_apps(username, password):
    from splunklib.client import connect

    try:    
        config = {
            "splunkd_scheme": get_conf_value('server', 'sslConfig', 'enableSplunkdSSL') and 'https' or 'http',
            "splunkd_port": get_conf_value('web', 'settings', 'mgmtHostPort').split(':')[1],
            "splunkd_host": get_conf_value('web', 'settings', 'mgmtHostPort').split(':')[0]
        }
    except Exception, e:
        print "There was an error retrieving configuration details from the Splunk instance specified."
        raise

    try:
        service = connect(
            scheme=str(config["splunkd_scheme"]),
            host=str(config["splunkd_host"]),
            port=int(config["splunkd_port"]),
            username=username,
            password=password)
            
        service.post("/services/apps/local/_reload") 
    except Exception, e:
        if hasattr(e, 'status') and e.status == 401:
            print "The Splunk credentials you provided are not valid. Please try again."
            sys.exit(1)
        elif hasattr(e, 'errno') and e.errno == 61:
            print "There was an error connecting to the Splunk instance you specified. Verify Splunk is running and try again."
            sys.exit(1)
        else:
            raise

@app.cmd
@app.cmd_arg('appname',     type=str, help='The name of app to deploy.')
@app.cmd_arg('--force',     action='store_true', help='Forces overwriting the /etc/apps/{name} directory (only on Windows).')
@app.cmd_arg('--file',      type=str, default=DEFAULT_SPLUNKDJ_CONFIG_FILE, help='The configuration file to read from.')
@app.cmd_arg('--username',  type=str, help='The Splunk username to deploy with.')
@app.cmd_arg('--password',  type=str, help='The Splunk password to deploy with.')
def deploy(appname, force, file, username, password):
    """Deploy (or redeploy) an application"""
    
    try:        
        config = setup_environment(file)
        app_path = path.join(MAIN_DIR, "server", "apps", appname)
        splunk_app_path = path.join(get_apps_base(), appname)
        
        while not username or not password:
            username = raw_input("Splunk username: ")
            password = getpass("Splunk password: ") 
            
        # We try a refresh initially to make sure we have good enough credentials
        # to perform this operation
        refresh_apps(username, password)
        
        if not path.exists(app_path):
            print "A framework app called '%s' doesn't exist. Try again using a different app name." % appname
            sys.exit(1)
            
        if path.exists(splunk_app_path) and HAS_LINK:
            os.unlink(splunk_app_path)            
            
        if not path.exists(splunk_app_path):
            if HAS_LINK:
                os.symlink(path.join(app_path, "splunkd"), splunk_app_path)
            else:
                shutil.copytree(path.join(app_path, "splunkd"), splunk_app_path)
        else:
            # If the user tells us to "force" redeployment and we don't have symlinks,
            # then we have to delete the copied over folder and write a new one
            if not HAS_LINK and force:
                shutil.rmtree(splunk_app_path)
                shutil.copytree(path.join(app_path, "splunkd"), splunk_app_path)
            elif not HAS_LINK and not force:
                print "There is already a '%s' app directory in /etc/apps. Try again using the '--force' parameter to overwrite it." % appname
                sys.exit(1)

        # Make sure splunkd is aware about this newly deployed app
        refresh_apps(username, password)

        print "The '%s' app was deployed." % appname
    except KeyboardInterrupt:
        pass
    

#  ___         _                     _             
# | _ \__ _ __| |____ _ __ _ ___    /_\  _ __ _ __ 
# |  _/ _` / _| / / _` / _` / -_)  / _ \| '_ \ '_ \
# |_| \__,_\__|_\_\__,_\__, \___| /_/ \_\ .__/ .__/
#                      |___/            |_|  |_|   
@app.cmd(name = 'package',     help="Prepares the specified app for deployment by packaging it into a single .spl file.")
@app.cmd_arg('appname',        type=str, help='The name of the app to package.')
@app.cmd_arg('--packagename',  type=str, default = None, 
             help='The output package name. Defaults to <appname>.spl')
def package(appname, packagename):
    if not packagename:
        packagename = path.join(os.getcwd(), appname + '.spl')
    elif packagename[0] != '/':
        packagename = path.join(os.getcwd(), packagename)

    source_dir = get_apps_base()
    splunk_app_path = path.join(source_dir, appname)

    if not path.exists(splunk_app_path):
        print "A Splunk app called '%s' doesn't exist. Try again using a different app name." % appname
        sys.exit(1)

    if os.path.isfile(packagename):
        print "There is already a package called '%s'. Move this existing package and try again." % (packagename)
        sys.exit(1)

    try:
        os.chdir(source_dir)
        tar_out = tarfile.open(packagename, 'w:gz')
        tar_out.add(appname + '/', recursive = True)
        tar_out.close()
        print "The '%s' app was packaged and the package is in the current directory as '%s.spl'" % (appname, appname)
    except Exception, e:
        print "An error occurred while deleting the '%s' app. Please try again." % appname
        raise

#  ___         _        _ _     _               ___              _ _     
# |_ _|_ _  __| |_ __ _| | |   /_\  _ __ _ __  | _ )_  _ _ _  __| | |___ 
#  | || ' \(_-<  _/ _` | | |  / _ \| '_ \ '_ \ | _ \ || | ' \/ _` | / -_)
# |___|_||_/__/\__\__,_|_|_| /_/ \_\ .__/ .__/ |___/\_,_|_||_\__,_|_\___|
#                                  |_|  |_|                              
@app.cmd(name = 'install',     help="Installs the specified packaged application.")
@app.cmd_arg('packagename',    type=str, help='The package file to install.')
@app.cmd_arg('--destination',  type=str, default = None, 
             help='The target directory to install to (the default location is $SPLUNK_HOME/etc/apps/).')
@app.cmd_arg('--username',     type=str, help='The Splunk username to deploy with.')
@app.cmd_arg('--password',     type=str, help='The Splunk password to deploy with.')
@app.cmd_arg('--norefresh',    action='store_true', help='Refreshes the installed apps in Splunk.')
def install(packagename, destination, username, password, norefresh):
    if not (os.path.isfile(packagename)):
        print "The package was not found at %s. Check the package name and try again." % packagename
        sys.exit(1)

    appname = packagename
    if appname.find(os.path.sep) != -1:
        appname = appname.split(os.path.sep)[-1]
    if appname.find('.') != -1:
        appname = appname.split('.')[0]
    
    if not destination:
        destination = get_apps_base()

    if packagename[0] != '/':
        packagename = path.join(os.getcwd(), packagename)

    splunk_app_path = path.join(destination, appname)
    if path.exists(splunk_app_path):
        print "There is already a Splunk app called '%s'." % appname
        sys.exit(1)

    if not norefresh:
        while not username or not password:
            username = raw_input("Splunk username: ")
            password = getpass("Splunk password: ")  
        refresh_apps(username, password)

    try:
        os.chdir(destination)
        tar_out = tarfile.open(packagename)
        tar_out.extractall()
        tar_out.close()

        refresh_apps(username, password)
        print "The '%s' app was installed at '%s'. Please restart Splunk." % (packagename, splunk_app_path)
    except Exception, e:
        print "An error occurred while installing the '%s' app. Please try again." % appname
        raise


#  ___                           _             
# | _ \___ _ __  _____ _____    /_\  _ __ _ __ 
# |   / -_) '  \/ _ \ V / -_)  / _ \| '_ \ '_ \
# |_|_\___|_|_|_\___/\_/\___| /_/ \_\ .__/ .__/
#                                   |_|  |_|   
@app.cmd(name = 'removeapp', help="Removes the specified app from Splunk.")
@app.cmd_arg('appname',     type=str, help='The name of the app to delete.')
@app.cmd_arg('--file',      type=str, default=DEFAULT_SPLUNKDJ_CONFIG_FILE, help='The configuration file to read from.')
@app.cmd_arg('--username',  type=str, help='The Splunk username to deploy with.')
@app.cmd_arg('--password',  type=str, help='The Splunk password to deploy with.')
@app.cmd_arg('--norefresh', action='store_true', help='Refreshes the installed apps in Splunk.')
def removeapp(appname, file, username, password, norefresh):
    splunk_app_path = path.join(get_apps_base(), appname)
        
    if not path.exists(splunk_app_path):
        print "An app named '%s' does not exist. Check the name and try again." % appname
        sys.exit(1)

    prompt = ("This will delete all files associated with the specified app!\n"
              "Are you sure you want to remove the '%s' app?") % appname
    if not confirm(prompt):
        print "Not removing '%s'" % appname
        sys.exit(0)

    try:
        if not norefresh:
            while not username or not password:
                username = raw_input("Splunk username: ")
                password = getpass("Splunk password: ")  
            
            # We try a refresh initially to make sure we have good enough credentials
            # to perform this operation
            refresh_apps(username, password)
            
        if path.exists(splunk_app_path):
           shutil.rmtree(splunk_app_path)
           
        if not norefresh:
            refresh_apps(username, password)
        
        print "The '%s' app was removed. Please restart Splunk." % appname
    except:
        print "An error occurred while deleting the '%s' app. Please try again." % appname

@app.cmd(name = 'createapp', help="Creates a new app using the specified name.")
@app.cmd_arg('appname',      type=str, help='The name of the app to create.')
@app.cmd_arg('--username',   type=str, help='The Splunk username to deploy with.')
@app.cmd_arg('--password',   type=str, help='The Splunk password to deploy with.')
@app.cmd_arg('--norefresh',  action='store_true', help='Refreshes the installed apps on Splunk.')
def createapp(appname, username, password, norefresh):
    
    try:            
        splunk_app_path = path.join(get_apps_base(), appname)
        
        if path.exists(splunk_app_path):
            print "There is already a Splunk app called '%s'. Try again using a different name." % appname
            sys.exit(1)
    except KeyboardInterrupt:
        pass
        
    try:        
        os.mkdir(splunk_app_path)
        
        template_path = path.join(MAIN_DIR, "server", "splunkdj", "app_templates", "splunkweb")
        template = "--template=%s" % template_path
        extensions = "--extension=py,xml,conf,tmpl"
        
        # NOTE: THIS MUST BE THE LAST EXTENSION!!
        # We depend on this to put the mount in the 
        # redirect.tmpl file in splunkd/appserver/templates
        mount = "--extension=%s" % get_conf_value('web', 'settings', 'root_endpoint')

        if not norefresh:
            while not username or not password:
                username = raw_input("Splunk username: ")
                password = getpass("Splunk password: ")  
                
            # We try a refresh initially to make sure we have good enough credentials
            # to perform this operation
            refresh_apps(username, password)
        
        run_django_command("startapp", [template, extensions, mount, appname, splunk_app_path], False)
        
        if not norefresh:
            # Make sure splunkd is aware about this new app
            refresh_apps(username, password)
        
        print "The '%s' app was created at '%s'. Please restart Splunk." % (appname, splunk_app_path)
    except KeyboardInterrupt:
        if path.exists(splunk_app_path):
            shutil.rmtree(splunk_app_path)
        pass
    except:
        if path.exists(splunk_app_path):
            shutil.rmtree(splunk_app_path)
        raise
    return

@app.cmd
@app.cmd_arg('appnames',        type=str, help='Apps to run tests for.', nargs="*")
@app.cmd_arg('--noinput',       action='store_true', default=True, help='Does not prompt the user for input of any kind.')
@app.cmd_arg('--failfast',      action='store_true', default=True, help='Stops running the test suite after the first failed test.')
@app.cmd_arg('--testrunner',    type=str, help='Uses the specified test runner class instead of the one specified by the TEST_RUNNER setting.')
@app.cmd_arg('--liveserver',    type=str, default=None, help='Overrides the default address where the live server (used with LiveServerTestCase) is expected to run from. The default value is localhost:8081.')
@app.cmd_arg('--file',          type=str, default=DEFAULT_SPLUNKDJ_CONFIG_FILE, help='The configuration file to read from.')
@app.cmd_arg('--username',      type=str, help='The Splunk username to run tests with.')
@app.cmd_arg('--password',      type=str, help='The Splunk password to run tests with.')
def test(appnames, noinput, failfast, testrunner, liveserver, file, username, password):
    """Runs the test suite for the specified applications, 
    or the entire site if no apps are specified."""
    
    appnames = " ".join(appnames)
    noinput = "--noinput" if noinput else ""
    failfast = "--failfast" if failfast else ""
    testrunner = "--testrunner=%s" % (testrunner) if testrunner else ""
    liveserver = "--liveserver=%s" % (liveserver) if liveserver else ""
    
    try:
        os.environ['TEST_MODE'] = "1"
        
        python = os.environ.get("PYTHON_HOME", None)
        if not python:
            print "Cannot run tests because system Python is not available."
            sys.exit(1)
        
        # The tests require a sqlite driver, so we have to append
        # the regular PYTHONPATH paths, otherwise we won't find it. It could be 
        # that we still won't find it, in which case we will just fail
        # with a useful error message
        path_info = envoy.run('%s -c "import json; import sys; print json.dumps(sys.path)"' % python)
        paths = json.loads(path_info.std_out or "[]")
        sys.path += paths
        
        # Store username and password if provided
        if username:
            os.environ['SPLUNK_TEST_USERNAME'] = username
        
        if password:
            os.environ['SPLUNK_TEST_PASSWORD'] = password
        
        # Try and import pysqlite2 or sqlite3. If both fail, then we stop
        if not try_import(['pysqlite2', 'sqlite3']):
            print "The framework couldn't import pysqlite2 or sqlite3, which are required for running tests."
            sys.exit(1)
        
        # Set SPLUNKDJ_CONFIG environment variable, which is used by settings.py
        setup_environment(file)
        
        args = filter(lambda x: len(x), [noinput, failfast, testrunner, liveserver, "--traceback", appnames])
        run_django_command("test", args)
    except KeyboardInterrupt:
        pass
    
    return

@app.cmd
@app.cmd_arg('--file', type=str, default=DEFAULT_SPLUNKDJ_CONFIG_FILE, help='Config file to read from')
def run(file):
    """Set up a new Web Framework Django server instance"""
    
    try:
        config = setup_environment(file)
        
        check_splunk()
        
        proxy = start_proxy(config)
        django = start_django(config)
        
        # Django internally uses a process fork to allow for code reloading,
        # so we give it a bit of time to catchup.
        sleep(2)
        print "The Splunk Web Framework is running now. Browse to http://localhost:%s/%s." % (config['proxy_port'], config['mount'])
        
        django.block()
    except KeyboardInterrupt:
        pass

@app.cmd
@app.cmd_arg('--file', type=str, default=DEFAULT_SPLUNKDJ_CONFIG_FILE, help='Config file to read from.')
def start(file):
    """Start Web Framework Django server in daemon mode"""
    if is_win32:
        print "The 'start' command is not supported on Windows."
        sys.exit(1)
    
    try:
        config = setup_environment(file)
        
        check_splunk()
        
        proxy = start_proxy(config, daemonize=True)
        django = start_django(config, daemonize=True)
        
        # Django internally uses a process fork to allow for code reloading,
        # so we give it a bit of time to catchup.
        sleep(2)
        print "The Splunk Web Framework is running now. Browse to http://localhost:%s/%s." % (config['proxy_port'], config['mount'])
    except KeyboardInterrupt:
        pass
    
@app.cmd
@app.cmd_arg('--file', type=str, default=DEFAULT_SPLUNKDJ_CONFIG_FILE, help='Config file to read from.')
def stop(file):
    """Stop Web Framework Django server in daemon mode"""
    if is_win32:
        print "The 'stop' command is not supported on Windows."
        sys.exit(1)
        
    try:
        config = setup_environment(file)
        
        stop_proxy(config)
        stop_django(config)
    except KeyboardInterrupt:
        pass
    
@app.cmd
@app.cmd_arg('--file', type=str, default=DEFAULT_SPLUNKDJ_CONFIG_FILE, help='Config file to read from.')
def restart(file):
    """Restart Web Framework Django server in daemon mode"""
    if is_win32:
        print "The 'restart' command is not supported on Windows."
        sys.exit(1)
        
    try:
        config = setup_environment(file)
        
        stop(file)
        start(file)
    except KeyboardInterrupt:
        pass

@app.cmd
@app.cmd_arg('--file', type=str, default=DEFAULT_SPLUNKDJ_CONFIG_FILE, help='Config file to delete.')
def clean(file):
    """Delete settings and configuration"""
    try:
        os.remove(file)
        os.remove(SPLUNK_HOME_FILE)
    except:
        print
        pass
    
@app.cmd
@app.cmd_arg('--file', type=str, default=DEFAULT_SPLUNKDJ_CONFIG_FILE, help='Config file to write to.')
@app.cmd_arg('--nodeploy', action='store_true', help='Deploys the default apps to Splunk.')
def setup(file, nodeploy):
    """Set up a new Web Framework Django server instance"""
        
    print "\nSetting up the Splunk Web Framework..."
    try:
        splunk_home = os.environ.get("SPLUNK_HOME", "")
        
        splunk_5                   = None
        splunkd_scheme             = None
        splunkweb_scheme           = None
        splunkd_port               = None
        splunkweb_port             = None
        splunkd_host               = None
        splunkweb_host             = None
        splunkweb_mount            = None
        splunkdj_mount             = None
        splunkdj_appserver_port    = None
        splunkdj_proxy_port        = None
        splunkdj_proxy_path        = None

        while True:
            version_info = envoy.run([['%s/bin/splunk' % splunk_home, 'version']])
            version = version_info.std_out.strip()
            if not (version.startswith("Splunk 5") or version.startswith("Splunk 6") or version.startswith("Splunk 201")):
                os.remove(path.join(MAIN_DIR, ".splunkhome"))
                print "The version must be >= 'Splunk 5.0', found '%s' in '%s'. Run 'splunkdj setup' and try again." % (version, splunk_home)
                sys.exit(1)

            if splunk_5 == None:
                splunk_5 = version.startswith("Splunk 5")

            # Get Python, Node and Splunk paths
            splunk_path = path.join(splunk_home, "bin", "splunk" + (".exe" if is_win32 else ""))
            python_path = path.join(splunk_home, "bin", "python" + (".exe" if is_win32 else ""))
            node_path = path.join(splunk_home, "bin", "node" + (".exe" if is_win32 else ""))
                
            python_exists = path.exists(python_path.strip())
            node_exists = path.exists(node_path)

            # Ensure Python and Node exist
            if not python_exists:
                print "No Python interpreter, exiting..."
                sys.exit(1)
                
            if not node_exists:
                print "No Node.js interpreter, exiting..."
                sys.exit(1)
        
            # Get Various information from Splunk
            if not splunkd_port:
                splunkd_port = get_conf_value("web", "settings", "mgmtHostPort").split(":")[1]
            
            if not splunkweb_port:
                splunkweb_port = get_conf_value("web", "settings", "httpport")
            
            if not splunkweb_mount:
                splunkweb_mount = get_conf_value("web", "settings", "root_endpoint")
                
            if not splunkd_scheme:
                is_splunkd_ssl = normalizeBoolean(get_conf_value("server", "sslConfig", "enableSplunkdSSL"))
                splunkd_scheme = "https" if is_splunkd_ssl else "http"
                
            if not splunkweb_scheme:
                is_splunkweb_ssl = normalizeBoolean(get_conf_value("web", "settings", "enableSplunkWebSSL"))
                splunkweb_scheme = "https" if is_splunkweb_ssl else "http"
            
            splunkd_scheme = splunkd_scheme or "https"
            splunkd_host = splunkd_host or "localhost"
            splunkweb_scheme = splunkweb_scheme or "http"
            splunkweb_host = splunkweb_host or "localhost"
            splunkweb_mount = splunkweb_mount or ""
            splunkdj_mount = splunkdj_mount or "dj"
            splunkdj_appserver_port = splunkdj_appserver_port or SPLUNKDJ_APPSERVER_DEFAULT_PORT
            splunkdj_proxy_port = splunkdj_proxy_port or SPLUNKDJ_PROXY_DEFAULT_PORT
            splunkdj_proxy_path = splunkdj_proxy_path or SPLUNKDJ_PROXY_DEFAULT_PATH
        
            print "\nThe Splunk Web Framework will use the following values:"
            print " - Splunkd scheme: %s" % splunkd_scheme
            print " - Splunkd host: %s" % splunkd_host
            print " - Splunkd port: %s" % splunkd_port
            print " - Splunk Web scheme: %s" % splunkweb_scheme
            print " - Splunk Web host: %s" % splunkweb_host
            print " - Splunk Web port: %s" % splunkweb_port
            print " - Splunk Web root endpoint: %s" % splunkweb_mount
            print " - Web Framework Django appserver port: %s" % splunkdj_appserver_port
            print " - Web Framework proxy port: %s" % splunkdj_proxy_port
            print " - Web Framework proxy path: %s" % splunkdj_proxy_path
            print " - Web Framework mount: %s" % splunkdj_mount
            print " - Splunk installation (SPLUNK_HOME): %s" % splunk_home
            print " - Splunk 5: %s" % splunk_5
            
            if confirm("\nAre these values correct ('y' to accept, 'n' to edit)", default=True):
                break
            
            splunkd_scheme = raw_input("Splunkd scheme [%s]: " % (splunkd_scheme)) or splunkd_scheme
            splunkd_host = raw_input("Splunkd host [%s]: " % (splunkd_host)) or splunkd_host
            splunkd_port = raw_input("Splunkd port [%s]: " % (splunkd_port)) or splunkd_port
            
            splunkweb_scheme = raw_input("Splunk Web scheme [%s]: " % (splunkweb_scheme)) or splunkweb_scheme
            splunkweb_host = raw_input("Splunk Web host [%s]: " % (splunkweb_host)) or splunkweb_host
            splunkweb_port = raw_input("Splunk Web port [%s]: " % (splunkweb_port)) or splunkweb_port
            splunkweb_mount = raw_input("Splunk Web mount [%s]: " % (splunkweb_mount)) or splunkweb_mount
            
            # Get information about Web Framework ports
            splunkdj_appserver_port = raw_input("Web Framework Django appserver port [%s]: " % (splunkdj_appserver_port)) or splunkdj_appserver_port
            while is_port_open("localhost", splunkdj_appserver_port):
                if confirm("Web Framework Django appserver port '%s' is taken. Would you like to change it" % splunkdj_appserver_port, default=True):
                    splunkdj_appserver_port = raw_input("Web Framework appserver port [%s]: " % (splunkdj_appserver_port)) or splunkdj_appserver_port
                else:
                    sys.exit(1)
            
            splunkdj_proxy_port = raw_input("Web Framework proxy port [%s]: " % (splunkdj_proxy_port)) or splunkdj_proxy_port
            while is_port_open("localhost", splunkdj_proxy_port):
                if confirm("Web Framework proxy port '%s' is taken. Would you like to change it" % splunkdj_proxy_port, default=True):
                    splunkdj_proxy_port = raw_input("Web Framework proxy port [%s]: " % (splunkdj_proxy_port)) or splunkdj_proxy_port
                else:
                    sys.exit(1)
        
            splunkdj_proxy_path = raw_input("Web Framework proxy path [%s]: " % splunkdj_proxy_path) or splunkdj_proxy_path
        
            splunkdj_mount = raw_input("Web Framework mount [%s]: " % splunkdj_mount) or splunkdj_mount
            
            splunk_home = raw_input("Splunk installation (SPLUNK_HOME) [%s]: " % splunk_home) or splunk_home
            splunk_home = path.expanduser(splunk_home)
            
            splunk_5 = normalizeBoolean(raw_input("Splunk 5 [%s]: " % splunk_5) or splunk_5)
            
            # Write out SPLUNK_HOME
            dot_splunkhome = open(path.join(MAIN_DIR, '.splunkhome'), 'w')
            dot_splunkhome.write(splunk_home)
            dot_splunkhome.flush()
                        
        # Serialize configuration
        create_config_file(
            config_file_path           = path.join(MAIN_DIR, file),
            splunkd_scheme             = splunkd_scheme,
            splunk_home                = splunk_home,
            splunkd_host               = splunkd_host,
            splunkd_port               = int(splunkd_port),
            splunkweb_scheme           = splunkweb_scheme,
            splunkweb_host             = splunkweb_host,
            splunkweb_port             = int(splunkweb_port),
            splunkweb_mount            = splunkweb_mount,
            x_frame_options_sameorigin = normalizeBoolean(get_conf_value("web", "settings", "x_frame_options_sameorigin")),
            mount                      = splunkdj_mount,
            raw_mount                  = splunkdj_mount,
            splunkdj_port              = int(splunkdj_appserver_port),
            proxy_port                 = int(splunkdj_proxy_port),
            proxy_path                 = splunkdj_proxy_path,
            debug                      = False,
            quickstart                 = False,
            splunk_5                   = splunk_5
        )
        
        if not nodeploy:
            print "\nInstalling default apps..."
            while True:
                username = raw_input("Splunk username: ")
                password = getpass("Splunk password: ")
                
                if not username or not password:
                    continue
                    
                args = Args(
                    appname="",
                    force=True,
                    file=DEFAULT_SPLUNKDJ_CONFIG_FILE,
                    username=username,
                    password=password,
                )
                for app in SPLUNKDJ_DEFAULT_APPS:
                    # Only deploy the default apps if they actually exist
                    app_path = path.join(MAIN_DIR, "server", "apps", app)
                    if not path.exists(app_path):
                        continue
                    
                    args.appname = app
                    deploy(args.appname, args.force, args.file, args.username, args.password)
                
                break
        
    except KeyboardInterrupt:
        print
        sys.exit(0)
        
    print "\nThe Splunk Web Framework setup is complete -- enter 'splunkdj run' to start."

def create_config_file(config_file_path=None, generate_secret_key=True, **kwargs):
    if config_file_path is None:
        raise Exception("You must provide a configuration file path.")
        
    if not "splunk_home" in kwargs:
        raise Exception("You must provide a value for SPLUNK_HOME.")
        
    original_config = {}
    if os.path.exists(config_file_path):
        try:
            original_config = json.load(open(config_file_path, 'r'))
        except:
            pass
        
    config_file = open(config_file_path, 'w')
    
    splunkd_scheme = kwargs.get("splunkd_scheme", "https")
    splunkd_host = kwargs.get("splunkd_host", "")
    splunkd_port = kwargs.get("splunkd_port", 0)
    splunkweb_scheme = kwargs.get("splunkweb_scheme", "http")
    splunkweb_host = kwargs.get("splunkweb_host", "")
    splunkweb_port = kwargs.get("splunkweb_port", 0)
    splunkweb_integrated = kwargs.get("splunkweb_integrated", False)
    # We have to strip all slashes to ensure we adhere to what splunkweb
    # does here
    splunkweb_mount = kwargs.get("splunkweb_mount", "").strip("/")
    x_frame_options_sameorigin = kwargs.get("x_frame_options_sameorigin", True)
    mount = kwargs.get("mount", "").strip("/")
    raw_mount = kwargs.get("raw_mount", "")
    splunkdj_port = kwargs.get("splunkdj_port", 0)
    proxy_port = kwargs.get("proxy_port", 0)
    # only strip the leading slash
    proxy_path = kwargs.get("proxy_path", "").rstrip("/")
    quickstart = kwargs.get("quickstart", True)
    splunk_home = kwargs.get("splunk_home")
    splunk_5 = kwargs.get("splunk_5")
    
    # Always use the current value (if one exists) for these settings
    use_built_files = original_config.get("use_built_files", True)
    use_minified_files = original_config.get("use_minified_files", True)
    debug = original_config.get("debug", kwargs.get("debug", False))
    
    is_win32 = sys.platform == "win32"

    # Get Python, Node and Splunk paths
    python_path = path.join(splunk_home, "bin", "python" + (".exe" if is_win32 else ""))
    node_path = path.join(splunk_home, "bin", "node" + (".exe" if is_win32 else ""))
    
    config = {
        "splunk_5"                   : splunk_5,
        "splunkd_scheme"             : splunkd_scheme,
        "splunkd_host"               : splunkd_host,
        "splunkd_port"               : int(splunkd_port),
        "splunkweb_scheme"           : splunkweb_scheme,
        "splunkweb_host"             : splunkweb_host,
        "splunkweb_port"             : int(splunkweb_port),
        "splunkweb_mount"            : splunkweb_mount,
        "splunkweb_integrated"       : splunkweb_integrated,
        "x_frame_options_sameorigin" : x_frame_options_sameorigin,
        "mount"                      : mount,
        "raw_mount"                  : raw_mount,
        "splunkdj_port"              : int(splunkdj_port),
        "proxy_port"                 : int(proxy_port),
        "proxy_path"                 : proxy_path,
        "debug"                      : debug,
        "python"                     : python_path,
        "node"                       : node_path,
        "quickstart"                 : quickstart,
        "use_built_files"            : use_built_files,
        "use_minified_files"         : use_minified_files
    }
    
    # Generate secret key
    has_secret_key = original_config.get("secret_key", None)
    if generate_secret_key or not has_secret_key:
        config['secret_key'] = generate_random_key()
        
    original_config.update(config)
        
    json.dump(original_config, config_file, sort_keys=True, indent=4)
    
    return original_config

if __name__=='__main__':
    app.run()
