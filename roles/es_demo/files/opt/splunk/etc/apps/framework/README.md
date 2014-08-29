# The Splunk Web Framework

#### Version 1.0 GA

The Splunk Web Framework lets developers quickly create custom Splunk apps by using prebuilt components, styles, templates, and reusable samples, and by adding custom logic, interactions, and UI. Applications developed with the Web Framework work seamlessly side by side with current Splunk applications.

The Splunk Web Framework uses the [Django web framework](https://www.djangoproject.com/), the [Splunk SDK for Python](https://github.com/splunk/splunk-sdk-python), and the [Splunk SDK for JavaScript](https://github.com/splunk/splunk-sdk-javascript). The Web Framework also depends on a few JavaScript libraries for the client-side of code, such as Backbone.js for eventing, and jQuery for working with the document object model (DOM).

The version of the Splunk Web Framework contained in this repository is designed to work in a standalone mode to work against Splunk 5.x. If you are using Splunk 6, the Splunk Web Framework is included within the core Splunk product. You can use the standalone version of the Web Framework with Splunk 6, but this is only useful for very specific and advanced use cases.

**Note** Significant changes have been made since the Preview release, such as names of components and APIs and the way components are instantiated in JavaScript. Any code you created for the Preview of the Splunk Web Framework will not work with the GA release. Overall concepts of the Web Framework remain the same. See the [Splunk Developer Portal](http://dev.splunk.com/view/web-framework/SP-CAAAER6) for more information.

If you have any questions, contact *devinfo@splunk.com*.


## Getting started

This section provides information about installing the Web Framework, running it, and creating an app.

* For full documentation, see the [Splunk Developer Portal](http://dev.splunk.com/view/web-framework/SP-CAAAER6).

* For information about the Web Framework components, see the [Splunk Web Framework Reference](http://docs.splunk.com/Documentation/WebFramework).


### Requirements
Here are the Web Framework requirements for this release:

* **Operating system**: Windows, Linux or Mac OS X.

* **Web browser**: Latest versions of Chrome, Safari, or Firefox; Internet Explorer 9 or later.

* **The Splunk Web Framework**: The Web Framework is available as a ZIP file from GitHub and as a Git repository.

* **Splunk**: Splunk 5.0 or later. If you haven't already installed Splunk, download it
[here](http://www.splunk.com/download).

    **Note** The Web Framework is already included with Splunk 6.0 and later.

* **Programming language**: Python 2.7.

### Install the Web Framework
The Web Framework installation package includes most of what you need to start building complete applications for Splunk, including:

* **The Django web framework**. Django 1.5.1 is included, even if you already have another installation of Django.

* **Programming tools**. The Splunk SDK for Python is included so that you can programmatically interact with the Splunk engine.

* **JavaScript tools**. The Web Framework include several JavaScript client frameworks such as jQuery, Backbone.js, and Bootstrap, along with our own Splunk SDK for JavaScript.

**To install the Web Framework**

You'll be using the **splunkdj** tool at the command line to work with the Splunk Web Framework. The **splunkdj** commands you can use are: `deploy`, `package`, `install`, `removeapp`, `createapp`, `test`, `run`, `start`, `stop`, `restart`, `clean`, and `setup`. To get help with the syntax, enter `splunkdj -h`.

**Note**  Windows users must run the **splunkdj** command-line tool with Administrator privileges. Otherwise, the process fails silently, without any errors.

1. Download and unzip the Web Framework ZIP file.
2. Open a command prompt, navigate to the directory where you unzipped the Web Framework (the **$WEBFRAMEWORK_HOME**).

   On Mac OS X and Unix, enter:

         ./splunkdj setup

   On Windows, enter:

         splunkdj setup

    The setup process asks you to specify where Splunk is installed, then displays the Splunk configuration variables that will be used, such as host names and port numbers. These values are taken from your current Splunk configuration settings, but you can use different values if you need to. After you accept these values (or opt to change them), setup installs the Web Framework and additional tools.

### Run the Web Framework

1. Start Splunk, if it's not running already.
2. At a command prompt, navigate to **$WEBFRAMEWORK_HOME**.

    On Mac OS X and Unix, enter:

        ./splunkdj run

    On Windows, enter:

        splunkdj run

3. Open *http://localhost:3000/dj* in a web browser to verify the Web Framework is working.

   Log in using your Splunk credentials, then you'll see the Web Framework home page listing all of the Web Framework apps on your system.


### Create an app
When you create an app, the framework generates the new app's directory and its files.

1. If the framework is running, stop it by pressing Ctrl+C at the command prompt.
2. At the command prompt, navigate to **$WEBFRAMEWORK_HOME**.

   On Mac OS X and Unix, enter the following, where *your_app_name* is the case-sensitive name of your app:

        ./splunkdj createapp your_app_name

   On Windows, enter:

        splunkdj createapp your_app_name

   You'll need to provide your Splunk credentials to create the app.

A *your_app_name* directory is created in **$SPLUNK_HOME/etc/apps/** with auto-generated project files, including:

   * **/default/app.conf**: Contains the meta data (author, description, version) for your app. Edit this file in a text editor to fill in the details. Note that you'll need to restart Splunk to see changes to this file.

   * **/django/your_app_name/templates/home.html**: The default home page, which is displayed when you go to *http://localhost:3000/dj/your_app_name/*.

To run your app:

1. Start the framework--at the command prompt, navigate to **$WEBFRAMEWORK_HOME**.

   On Mac OS X and Unix, enter:

        ./splunkdj run

   On Windows, enter:

        splunkdj run

2. Open the Web Framework home page at *http://localhost:3000/dj*, where you'll see your new app listed with the other apps.

  **Note** These apps are also displayed in Splunk Web, but you can't run them from the Splunk Web port. The Web Framework apps can only be run in the Web Framework proxy port, which is 3000 by default.

### Documentation

To learn how to use the Web Framework, see the Web Framework on the [Splunk Developer Portal](http://dev.splunk.com/view/web-framework/SP-CAAAER6). 

The documentation applies to the integrated version of the Web Framework in Splunk 6.0 and later. However, if you are using the stand-alone version of the Web Framework, there are a few differences to note: 

   * The SplunkMap view is not supported in Splunk 5.0. Use GoogleMap view instead. The path for this view is `splunkjs/mvc/googlemapview`, and the template tag is `{% googlemap %}`. 

   * Where the documentation uses the Splunk Web port (8000), use the Web Framework proxy port (3000) instead. 

   * Where the documentation instructs you to restart Splunk Web, restart the Web Framework instead (`splunkdj run`).  


## Repository

<table>

<tr>
<td><em>cli</em></td>
<td>This directory contains the Splunk Web Framework utility script</td>
</tr>

<tr>
<td><em>contrib</em></td>
<td>This directory contains third-party tools and libraries</td>
</tr>

<tr>
<td><em>proxy</em></td>
<td>This directory contains the development web server</td>
</tr>

<tr>
<td><em>server</em></td>
<td>This directory contains the source for the framework and apps</td>
</tr>

</table>


### Branches

The **master** branch always represents a stable and released version of the framework.


## Documentation and resources

When you need to know more:

* For all things developer with Splunk, your main resource is the [Splunk Developer Portal](http://dev.splunk.com).

* For conceptual and how-to documentation, see the [Overview of the Splunk Web Framework](http://dev.splunk.com/view/web-framework/SP-CAAAER6).

* For component reference documentation, see the [Splunk Web Framework Reference](http://docs.splunk.com/Documentation/WebFramework).

* For more about Splunk in general, see [Splunk>Docs](http://docs.splunk.com/Documentation/Splunk).


## Community

Stay connected with other developers building on Splunk.

<table>

<tr>
<td><b>Email</b></td>
<td>devinfo@splunk.com</td>
</tr>

<tr>
<td><b>Issues</b>
<td>https://github.com/splunk/splunk-appframework/issues/</td>
</tr>

<tr>
<td><b>Answers</b>
<td>http://splunk-base.splunk.com/tags/appfx/</td>
</tr>

<tr>
<td><b>Blog</b>
<td>http://blogs.splunk.com/dev/</td>
</tr>

<tr>
<td><b>Twitter</b>
<td>@splunkdev</td>
</tr>

</table>


### How to contribute

If you would like to contribute to the framework, go here for more information:

* [Splunk and open source](http://dev.splunk.com/view/opensource/SP-CAAAEDM)

* [Individual contributions](http://dev.splunk.com/goto/individualcontributions)

* [Company contributions](http://dev.splunk.com/view/companycontributions/SP-CAAAEDR)

## Support

This GA version of the Splunk Web Framework is officially supported by the [Splunk Support Team](http://www.splunk.com/support).

Please feel free to open issues and provide feedback either through GitHub Issues or by contacting the team directly.

## Contact Us

You can reach the Developer Platform team at _devinfo@splunk.com_.

## License
The Splunk Web Framework is licensed under the Apache License 2.0. Details can be found in the LICENSE file.