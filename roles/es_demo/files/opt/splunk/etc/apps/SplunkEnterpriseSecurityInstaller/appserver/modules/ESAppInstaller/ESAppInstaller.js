/**
 * Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
 */
var appInstallerSecureRedirect = true;
var appInstallerState = null;
var arrAppState = ["DISABLE","RESTART","COMPARE","UPGRADE"];
Splunk.Module.ESAppInstaller = $.klass(Splunk.Module, {

    initialize: function($super,container) {
        var retVal = $super(container);
        var moduleThis = this;
        this.checkInstalledVersion(moduleThis);
        
        $('#progressModal')
            .ajaxStart(function() {
                $(this).modal("show");
            })
            .ajaxStop(function() {
                $(this).modal("hide");
            });
        
        $("#btn-print").click(function(event){
            var win = window.open();
            win.focus();
            win.document.open();
            win.document.write('<html><head></head><body>');
            win.document.write($("#fileTextArea").val().replace(/\n/gi,'<br>'));
            win.document.write('</body></html>');
            win.document.close();
            win.print();
            win.close();
        });
        
        $("#btn-recheck").click(function(event){

            console.log("btn-recheck.click");

            ajaxObj = {
                url: Splunk.util.make_url('custom','SplunkEnterpriseSecurityInstaller','es_installer_controller','show'),
                cache: false,
                type: "POST",
                "datatype": "json"
            }

            ajaxObj.data = {step:"diff"};                                                
            ajaxObj.success = function(json) {moduleThis.actionShowReports(json);};
            $.ajax(ajaxObj);

        });        

        $("#btn-continue", this.container).click(function(event) {

            console.log("btn-continue.click");
            console.log("appInstallerState:" + appInstallerState);
            if (appInstallerState === "RESTART") {
                //call restart
                moduleThis.restartSplunk();
            }
            
            else {

                ajaxObj = {
                    url: Splunk.util.make_url('custom','SplunkEnterpriseSecurityInstaller','es_installer_controller','show'),
                    cache: false,
                    type: "POST",
                    "datatype": "json"
                }
            
                if (appInstallerState === "DISABLE") {
                    //do something
                    console.log("state===DISABLE");
                    ajaxObj.data = {step:"disable"};
                    ajaxObj.success = function(json) {moduleThis.actionDisableApp(json);};
                    $.ajax(ajaxObj);
                }

                if (appInstallerState === "COMPARE") {
                        console.log("state===COMPARE");

                        //uppack
                        ajaxObj.data = {step:"package"};
                        ajaxObj.success = function(json) {
                            //alert("uppacked");
                        };
                        $.ajax(ajaxObj);

                        //diff
                        ajaxObj.data = {step:"diff"};                                                
                        ajaxObj.success = function(json) {moduleThis.actionShowReports(json);};
                        $.ajax(ajaxObj);
                }
                
                if (appInstallerState === "UPGRADE") {
                    //do something
                    console.log("state===UPGRADE");
                    ajaxObj.data = {step:"upgrade"};
                    ajaxObj.success = function(json) {moduleThis.actionUpgradeApp(json);};
                    $.ajax(ajaxObj);
                }
                
                if (appInstallerState === "INSTALL") {
                    //do something
                    console.log("state===INSTALL");
                    ajaxObj.data = {step:"install"};
                    ajaxObj.success = function(json) {moduleThis.actionInstallApp(json);};
                    $.ajax(ajaxObj);
                }
                         
            }
        });

        return retVal;
    },

    checkInstalledVersion: function(context) {

        // field/state for restart at first load of installer
        // this will be modified based on existence of restart messages of the 'messages' endpoint
        this.restartNeeded = false;
        
        // field/state to determine http vs https URL after restart
        // this will be modified based on enable/disable keywords in the restart messages of the 'messages' endpoint
        this.secureRedirect = false;

        //check for restart at the very beginning in case something was completed but page was reloaded.
        //this preserves the RESTART state if current state was post disable, upgrade or install steps.        
        $.ajax({
            type: "GET",
            url: Splunk.util.make_url("/splunkd/messages?output_mode=json&count=-1"),
            async: false,
            cache: false,
            success: function(data) {
                entries = data.entry;
                for(var e = 0; e < entries.length; e++){
                
                    // message name
                    entry = entries[e].name;
                    
                    // message content/body
                    msg = entries[e].content.message;
                    
                    console.log("entry=" + entry + "; message=" + msg);
                    
                    if (entry.indexOf("restart_required") != -1) {
                    
                        // given that this is a restart message, we check if it has anything to do with ES apps
                        // source.package.foldername == SplunkEnterpriseSecuritySuite
                        // package.output.foldername == SplunkEnterpriseSecurityInstaller
                        if (msg.match(/(SA-[a-zA-Z0-9-_]+)|(DA-[a-zA-Z0-9-_]+)|(SplunkEnterpriseSecuritySuite)|(SplunkEnterpriseSecurityInstaller)|(Splunk_[D|S|T]A_[a-zA-Z0-9-_]+)/ig) != null) {
                            this.restartNeeded = true;
                            
                            // if any of these restart messages contain 'enable' we know that ES will be on https
                            if (msg.indexOf("enable") != -1) {
                                this.secureRedirect = true;
                            }
                        }
                    }
                }
            }.bind(this)
        });
        
        if (this.restartNeeded) {
            //put up the restart needed view
            $("#pane_restart_needed_msg").show();
            $("#btn-continue").html('<i class="icon-repeat icon-white"></i>Restart');
            appInstallerState = "RESTART";
            context.updateState();
            context.updateUI();
            appInstallerSecureRedirect = this.secureRedirect;
        }
        
        else {
            
            // restart is not needed, proceed with upgrade
            var url = Splunk.util.make_url('custom','SplunkEnterpriseSecurityInstaller','es_installer_controller','show');
            $.ajax({
                url: url,
                cache: false,
                type: 'POST',
                data: {
                    step:'check'
                },
                'dataType': 'json',
                success: function(json) {
                    if (json["success"])  {

                        var installAction = json.data[0];
                        var installedVersion = json.data[1];
                    
                    
                        //app is installed, DISABLE it
                        if (installAction == "DISABLE") {
                            // show disable app message
                            $("#pane_disabled_false_msg").show();
                            appInstallerState = "DISABLE";
                            console.log("check: state => DISABLE");
                            context.updateState();
                            context.updateUI();
                            appInstallerSecureRedirect = false;
                        }
                
                        //No app is installed, perform installation
                        else if (installAction == "INSTALL") {
                            $(".super-list > a").css("opacity", "0.3");
                            $("#pane_install_msg").show();
                            $("#btn-continue").html('<i class="icon-cog icon-white"></i>Install');
                            appInstallerState = "INSTALL";
                            console.log("check: state => INSTALL");
                        }
                    
                        //installed < release, perform minor/maint upgrade
                        else if (installAction == "UPGRADE_MAJOR" || installAction == "UPGRADE_MINOR" || installAction == "UPGRADE_MAINT" || installAction == "UPGRADE_BUILD") {
                            $("#pane_upgrade_ready_msg").show();
                            $("#btn-continue").html('<i class="icon-cog icon-white"></i>Continue');
                            appInstallerState = "COMPARE";
                            console.log("check: state => COMPARE");
                            context.updateState();
                            context.updateUI();
                    
                        }
                    
                        else if (installAction == "NOOP") {
                        
                            console.log("check: NOOP");
                            //remove continue button
                            $("#btn-continue").hide();
                            //The most recent is installed, allow user to exit upgrader app
                            $(".installedVersionString").text(installedVersion);
                            $("#pane_upgrade_installed_msg").show();
                            $(".super-list > a").css("opacity", "0.3");
                        }
                    
                        else if (installAction == "UNSUPPORTED") {
                            console.log("check: UNSUPPORTED");
                            //remove continue button
                            $("#btn-continue").hide();
                            //The most recent is installed, allow user to exit upgrader app
                            $(".installedVersionString").text(installedVersion);
                            $("#pane_upgrade_unsupported_msg").show();
                            $(".super-list > a").css("opacity", "0.3");
                        
                        }

                        else if (installAction == "SERVER_UNSUPPORTED") {
                            console.log("check: SERVER UNSUPPORTED");
                            //remove continue button
                            $("#btn-continue").hide();
                            //The most recent is installed, allow user to exit upgrader app
                            $(".installedVersionString").text(installedVersion);
                            $("#pane_upgrade_unsupported_server_msg").show();
                            $(".super-list > a").css("opacity", "0.3");
                        }                    
                    
                        else {
                            //do nothing
                            console.log("ERROR - NOTHING DONE");
                        }
                    
                    }
                
                    else {
                        //this.continueUpgrade = false;
                        var messenger = Splunk.Messenger.System.getInstance();
                        messenger.send('error', "this_string_effectively_means_nothing", _('ERROR - ') + json["messages"][0]["message"] || json);

                    }
                }
            });
        }
    },
    
    restartSplunk: function() {

        if (!confirm(_("Are you sure you want to restart Splunk?"))) {
            return false;
        }


        var restart_url_base;
    
        $.post(Splunk.util.make_url('/api/manager/control'), {operation: 'restart_server'}, function(data) {
            if (data.status=='OK') {

                $('.splOverlay').show();
                $('#restartstatus').show();                

            } else if (data.status == 'PERMS') {
                return Splunk.Messenger.System.getInstance().send('error', 'restart_server', 'Permission Denied - You are not authorized to restart the server');
            } else if (data.status == 'AUTH') {
                return Splunk.Messenger.System.getInstance().send('error', 'restart_server', 'Restart failed');
            } else if (data.status == 'FAIL') {
                return Splunk.Messenger.System.getInstance().send('error', 'restart_server', 'Restart failed: '+data.reason);
            } else {
                return Splunk.Messenger.System.getInstance().send('error', 'restart_server', 'Restart failed');
            }
        }, 'json');
    
        return true;
    },
    
    actionDisableApp: function(json) {

        if (json["success"]) {
            $("#pane_disabled_false_msg").hide();
            $("#pane_disabled_true_msg").show();
            $("#btn-continue").html('<i class="icon-repeat icon-white"></i>Restart');
            appInstallerState = "RESTART";
            console.log("actionDisableApp: state => RESTART");
            this.updateState();
            this.updateUI();
        }
        else {
            var messenger = Splunk.Messenger.System.getInstance();
            messenger.send('error', "this_string_effectively_means_nothing", _('ERROR - ') + json["messages"][0]["message"] || json);

        }

    },
    
    actionShowReports: function(json) {

        if (json["success"]) {
            var result = json.data[0];
            var printMsg = "";
            
            var deprecatedAppsResult = this.composeDeprecatedAppsReport(result);
            var deprecatedAppsCount = deprecatedAppsResult[0];
            var deprecatedAppsText = deprecatedAppsResult[1];
            printMsg += deprecatedAppsText;

            var deprecatedFilesResult = this.composeDeprecatedFilesReport(result);
            var deprecatedFilesCount = deprecatedFilesResult[0];
            var deprecatedFilesText = deprecatedFilesResult[1];
            printMsg += deprecatedFilesText;

            var defaultConfResult = this.composeDefaultConfsReport(result);
            var defaultConfCount = defaultConfResult[0];
            var defaultConfText = defaultConfResult[1];
            printMsg += defaultConfText;

            var customizationResult = this.composeCustomizationReport(result);
            var customizationCount = customizationResult[0];
            var customizationText = customizationResult[1];
            printMsg += customizationText;

            //append to hidden textarea for printing
            $("#fileTextArea").val(printMsg);
            $("#pane_upgrade_ready_msg").hide();
            
            //show print and recheck buttons
            $("#div-recheck").show();
            $("#div-print").show();
            $("#pane_report_tabs").show();
            
            //remove any previous offset classes set for this button
            $("#div-continue").removeClass(
                function (index, css) {
                    return (css.match (/\boffset\S+/g) || []).join(' ');
            });

            $("#btn-continue").html('<i class="icon-cog icon-white"></i>Upgrade & Restart');
            appInstallerState = "UPGRADE";
            console.log("actionShowReports: state => UPGRADE");
            $(".sub-list").show();
            this.updateState();
            this.updateUI();

            this.updateIndicators("customizations", customizationCount);
            this.updateIndicators("deprecated-apps", deprecatedAppsCount);
            this.updateIndicators("deprecated-files", deprecatedFilesCount);
            this.updateIndicators("default-confs", defaultConfCount);
        }
        else {
            var messenger = Splunk.Messenger.System.getInstance();
            messenger.send('error', "this_string_effectively_means_nothing", _('ERROR - ') + json["messages"][0]["message"] || json);

        }
    },
    
    composeDeprecatedAppsReport: function(result) {

        var deprecatedFolders = result["deprecatedApps"];
        var printText = "<p><h2>Deprecated Apps</h2></p>";
        var deprecatedCount = 0;

        var taCiscoMsg = "<u>TA-cisco Detected</u>" +
            "<p>The general purpose Cisco Technology Add-On has been deprecated because the following Cisco apps have been updated to provide the necessary knowledge layers.</p>" +
            "<ul>" + 
            "<li> <a href='http://splunk-base.splunk.com/apps/22292/splunk-for-cisco-ips' target='_blank'>Splunk for Cisco IPS</a></li>" +
            "<li> <a href='http://splunk-base.splunk.com/apps/22303/splunk-for-cisco-firewalls' target='_blank'>Splunk for Cisco Firewalls</a></li>" +
            "<li> <a href='http://splunk-base.splunk.com/apps/22304/splunk-for-cisco-client-security-agent' target='_blank'>Splunk for Cisco Client Security Agent</a></li>" +
            "<li> <a href='http://splunk-base.splunk.com/apps/22305/splunk-for-cisco-ironport-email-security-appliance' target='_blank'>Splunk for Cisco IronPort Email Security Appliance</a></li>" +
            "<li> <a href='http://splunk-base.splunk.com/apps/22302/splunk-for-cisco-ironport-web-security-appliance' target='_blank'>Splunk for Cisco IronPort Web Security Appliance</a></li>" +
            "<li> <a href='http://splunk-base.splunk.com/apps/22306/splunk-for-cisco-mars' target='_blank'>Splunk for Cisco MARS</a></li>" +
            "</ul>" +
            "<p>The existing TA-Cisco has been retained so that modifications do not need to be re-implemented.</p>";

        var taNixMsg = "<u>Deprecated TA-nix Detected</u><br/>This app has been deprecated and replaced by Splunk_TA_nix.  " +
            "TA-nix will be disabled after upgrade.  For more information, read <a href='http://docs.splunk.com/Documentation/ES/Install/Beforeupgrading#Splunk_App_for_.2ANix' target='_blank'>here</a>";
        var taDeploymentAppsMsg = "<u>Deprecated TA-deployment-apps Detected</u><br/>This app has been deprecated and replaced by Splunk_TA_nix.  " +
            "TA-deployment-apps will be disabled after upgrade.  For more information, read <a href='http://docs.splunk.com/Documentation/ES/Install/Beforeupgrading#Splunk_App_for_.2ANix' target='_blank'>here</a>";

        var taCheckpoint = "<u>Deprecated TA-checkpoint Detected</u><br/>This app has been deprecated and no longer included with future releases of Splunk App for Enterprise Security.  " +
            "However, the existing TA-checkpoint will remain enabled after upgrade.  TA-checkpoint is superseded by Splunk Add-on for Check Point OPSEC LEA.  You can download Splunk Add-on for Check Point OPSEC LEA from Splunkbase.  For more information, read <a href='http://splunk-base.splunk.com/apps/search/?q=opsec' target='_blank'>here</a>";

        var taNessusMsg = "<u>Deprecated TA-nessus Detected</u><br/>This app has been deprecated and replaced by Splunk_TA_nessus.  TA-nessus will be disabled after upgrade.";

        var saCIM = "<u>Deprecated SA-CommonInformationModel Detected</u><br/>This app has been deprecated and replaced by Splunk_SA_CIM. SA-CommonInformationModel will be disabled after upgrade.";
        
        var taIp2locationMsg = "<u>Deprecated TA-ip2location Detected</u><br/>This app has been deprecated and replaced by Splunk Enterprise iplocation search command. TA-ip2location will be disabled after upgrade.";
        
        var taFlowd = "<u>Deprecated TA-flowd Detected</u><br/>This app has been deprecated and will not be updated with future releases of Splunk App for Enterprise Security.";
        
        var taMcafeeMsg = "<u>Deprecated TA-mcafee Detected</u><br/>This app has been deprecated and replaced by Splunk_TA_mcafee.  TA-mcafee will be disabled after upgrade.";

        var deprecatedAppsMap = {"TA-cisco":taCiscoMsg , "TA-deployment-apps":taDeploymentAppsMsg, "TA-nix":taNixMsg, "TA-checkpoint":taCheckpoint, "SA-CommonInformationModel":saCIM, "TA-nessus":taNessusMsg, "TA-ip2location":taIp2locationMsg, "TA-flowd":taFlowd, "TA-mcafee":taMcafeeMsg};

        var deprecatedAppFound = false;
        var deprecatedAppMsg = "";
        for (var i=0; i<deprecatedFolders.length; i++) {
            for (var appName in deprecatedAppsMap) {
                if (deprecatedFolders[i].search(new RegExp(appName, "i")) > -1) {
                    deprecatedAppFound = true;
                    deprecatedAppMsg += deprecatedAppsMap[appName] + "<br/><br/>";
                    printText += deprecatedAppsMap[appName] + "<br/><br/>";
                    deprecatedCount++;
                }
            }
        }
        
        if (deprecatedCount < 1) {
            deprecatedAppMsg = "<p>No Deprecated Apps Found</p>";
        }

        $("#report-content-deprecated-apps").html(deprecatedAppMsg);
        return [deprecatedCount, printText];
    },
    
    composeDeprecatedFilesReport: function(result) {

        var deprecatedFilesJson = result["deprecatedFiles"];
        var printText = "<p><h2>Deprecated Files</h2></p>";
        var deprecatedFilesCount = 0;
        var depFilesTitle = "<u>Deprecated Files Detected</u>";
        var depFilesDesc = "<br>The following files are no longer in use and deprecated.  Future versions of ES will remove these files.";
        var depFilesList = '<br/><br/><div id="dep-files"><ul id="dep-files-list"></ul></div>';
        
        $("#report-content-deprecated-files").append(depFilesTitle, depFilesDesc, depFilesList);
        printText += depFilesTitle + depFilesDesc;
        
        var fileList = [];
        var addList = function(listName, listText, listClass) {
            var li = $('<li/>')
                .addClass(listClass)
                .appendTo($(listName));
            var aaa = $('<a/>')
                .addClass(listClass)
                .text(listText)
                .appendTo(li);
        }
        for (var appName in deprecatedFilesJson) {
            addList("#dep-files-list", appName, "dep-li-zero");
            fileList = deprecatedFilesJson[appName];
            deprecatedFilesCount++;
            for (var i = 0; i < fileList.length; i++) {
                addList("#dep-files-list", fileList[i], "dep-li-first");
                printText += fileList[i] + "<br/>";
            }
        }
        return [deprecatedFilesCount, printText];
    },
    
    composeDefaultConfsReport: function(result) {

        //Messages to display in the report divs after file comparison is completed                        
        var defaultMsg = "<u>Detected Modified Default Configuration Files</u><br/><p>The files listed below were modified." +
            "They will be overwritten when the installation takes place. If you would like to keep these files, please copy them to an appropriate location.</p>";
        var extensionMsg = "<u>Detected Extension Files</u><br/><p>The following files are new 'extension' files. They will be unaffected by the upgrade.</p>";

        var defaultCount = 0;
        var printText = "";
        
        //flag to indicate there was a successful comparison completed
        var diff = result["diff"];
        
        //Report the results of the file comparison IFF there was an MD5 available for the installed version
        if (!diff) {

            //display the filelist of extensions and modified default files
            $("#report-content-default-conf").html("<p>Unable to determine file diffs.  No MD5 list for version installed</p>");
            defaultCount++;
        }

        else {

            var defaultFiles = ( result["defaultFiles"] == "" ? "<br><p>No modified default files found.</p>" : result["defaultFiles"] );
            var extensionFiles = ( result["extensionFiles"] == "" ? "<br><p>No extension files found.</p>" : result["extensionFiles"] );

            //$("#report-content-default-conf").html(defaultMsg + defaultFiles);
            
            var docText = "<p>Please refer to the Splunk App for Enterprise Security " + 
    "<a href='http://docs.splunk.com/Documentation/ES/3.1/Install/Upgradetonewerversion#Resolve_warnings_and_conflicts' target='_blank'>" +
    " Installation and Configuration Manual</a> for additional information on any warnings detected.</p>"
            
            $("#report-content-default-conf").html(docText + "<hr>" + defaultMsg + defaultFiles + "<br/><hr><br/>" + extensionMsg +  extensionFiles);
            printText += "<p><h2>Modified Default Files</h2></p>" + defaultMsg + defaultFiles;
            printText += "<p><h2>Extension Files</h2></p>" + extensionMsg +  extensionFiles;

            //each conflict is delimited by newline (<br>) we'll count those ...
            var matchDefault = result["defaultFiles"].match(/\<br\>/g);
            var matchExtensions = result["extensionFiles"].match(/\<br\>/g);
            var countDefault = ( matchDefault == null ? 0 : matchDefault.length );
            var countExtentions = ( matchExtensions == null ? 0 : matchExtensions.length );

            defaultCount = countDefault + countExtentions;
        }
        
        return [defaultCount, printText];
    },
    
    composeCustomizationReport: function(result) {
        var conflictsDict = result["conflicts"];
        var customizationCount = 0;
        var tsidxCount = 0;
        var liteViewCount = 0;
        var localNavCount = 0;
        
        var printText = "";

        var localNavText = "";
        var localNav = result["localNav"]
        if (localNav != null && localNav !="None") {
            localNavCount++;
            localNavText += "<p><u>A custom navigation file is detected</u></p>";
            localNavText += "<ul><li>" + localNav + "</li></ul><br>";
            localNavText += "This custom navigation file prevents updates to be deployed with the new navigation.  ";
            localNavText += "This custom file will be renamed (default.xml.old) and disabled after the upgrade.  ";
            localNavText += "Re-visit this custom navigation file if you want to reinstate changes.";
        }

        var tsidxConf = conflictsDict["tsidx"];
        var tsidxText = "<p><u>TSIDX Conflicts</u></p>";

        var liteViewsDict = conflictsDict["liteViews"];
        var liteViewsDictText = "<p><u>Navigation Lite View Differences</u></p>";

        for (var key in tsidxConf) {
            tsidxText += "File: " + key + "<ul>";
            for (var i=0; i<tsidxConf[key].length; i++) {
                tsidxText += "<li>" + tsidxConf[key][i] + "</li>";
                tsidxCount++;
            }
            tsidxText += "</ul>";
        }
        
        if (tsidxCount < 1) {
            tsidxText += "<ul><li>No Issues Found</li></ul>";
        }

        for (var key in liteViewsDict) {
            liteViewsDictText += "File: " + key + "<ul>";
            for (var i=0; i<liteViewsDict[key].length; i++) {
                liteViewsDictText += "<li>" + liteViewsDict[key][i] + "</li>";
                liteViewCount++;
            }
        }
        
        if (liteViewCount < 1) {
            liteViewsDictText += "<ul><li>No Issues Found</li></ul>";
        }

        var globalConfConflicts = conflictsDict["globalConfConflicts"];
        //each conflict is delimited by list items (<li>) we'll count those ...
        var matchGlobal = globalConfConflicts.match(/\<li\>/g);
        var countGlobal = ( matchGlobal == null ? 0 : matchGlobal.length );
        customizationCount = tsidxCount + liteViewCount + countGlobal + localNavCount;

        var conflictsDocText = "<p>The following detected configuration customizations require further examination after this upgrade. " +
                "Additional file migration may be necessary.  Please refer to the Enterprise Security " + 
                "<a href='http://docs.splunk.com/Documentation/ES/3.1/Install/Upgradetonewerversion#Resolve_warnings_and_conflicts' target='_blank'>" +
                " Installation and Configuration Manual.</a></p>"

        var conflictsText = conflictsDocText + "<hr>" + globalConfConflicts + "<hr>" + tsidxText + "<hr>" + liteViewsDictText + "<hr>" + localNavText;

        $("#report-content-customizations").html(conflictsText);
        printText += "<p><h2>Configuration Customizations</h2></p>" + conflictsText;

        return [customizationCount, printText];
    },

    actionUpgradeApp: function(json) {
        if (json["success"]) {
            appInstallerState = "RESTART";
            console.log("actionUpgradeApp: state => RESTART");
            
            if (!this.restartSplunk()) {
                //
                $("#pane_report_tabs").hide();
                $("#pane_upgrade_success_msg").show();
                $("#btn-exit").hide();
                $("#div-recheck").hide();
                $("#div-print").hide();
                $("#btn-continue").html('<i class="icon-repeat icon-white"></i>Restart');
                
                //remove any previous offset classes set for this button
                $("#div-continue").removeClass(
                    function (index, css) {
                        return (css.match (/\boffset\S+/g) || []).join(' ');
                });
                
                $("#div-continue").addClass("offset6");
                appInstallerState = "RESTART";
                //this.updateState();
                //this.updateUI();
            }
            else {
                //do nothing            
            }
        }
        else {
            var messenger = Splunk.Messenger.System.getInstance();
            messenger.send('error', "this_string_effectively_means_nothing", _('ERROR - ') + json["messages"][0]["message"] || json);
        }
    
    },
    
    actionInstallApp: function(json) {
        if (json["success"]) {
            appInstallerState = "RESTART";
            console.log("actionInstallApp: state => RESTART");
            
            if (!this.restartSplunk()) {
                $("#pane_install_msg").hide();
                $("#pane_install_success_msg").show();
                $("#btn-continue").html('<i class="icon-repeat icon-white"></i>Restart');
                
                //remove any previous offset classes set for this button
                $("#div-continue").removeClass(
                    function (index, css) {
                        return (css.match (/\boffset\S+/g) || []).join(' ');
                });
                
                $("#div-continue").addClass("offset6");
                appInstallerState = "RESTART";
            }
            else {
                //do nothing            
            }
        }
        else {
            var messenger = Splunk.Messenger.System.getInstance();
            messenger.send('error', "this_string_effectively_means_nothing", _('ERROR - ') + json["messages"][0]["message"] || json);
        }
    
    },

    updateState: function() {
        while (arrAppState.length > 0) {
            tmpState = arrAppState.shift();
            console.log("updateState => tmpState:" + tmpState);
            if (tmpState.toLowerCase() === appInstallerState.toLowerCase()) {
                console.log("updateState: tmpStateEquals");
                return null;
            }
        }
    },
    
    updateUI: function() {
        console.log("updateUI");
        console.log("arrAppState before:" + arrAppState);
        
        if (arrAppState < 1) {

            $(".super-list > a").each(function() {
                $(this).css("opacity", "1");
                console.log("css change 1.0");
            });
        }
        else {
            for (var i=0; i < arrAppState.length; i++) {
                tmpState = arrAppState[i];
                console.log("for loop tmpstate:" + tmpState);
                $(".super-list > a").each(function() {
                    console.log("li:" + $(this).attr('id'));
                    if ( ($(this).attr('id').toLowerCase()).indexOf(tmpState.toLowerCase()) > 0) {
                        //shade this li > a
                        $(this).css("opacity", "0.3");
                        console.log("css change 0.3");                    
                    }
                }); 
            }
            console.log("arrAppState after:" + arrAppState);
        }
    },
    
    updateIndicators: function(indicatorName, numError) {
        if (numError < 1) {
            
            //update list nav
            $("#li-" + indicatorName + " > #list-count").text(" (0)");
            $("#li-" + indicatorName + " > .circle-small").css("background", "green");
            
            //update circle indicator
            $("#indicator-" + indicatorName).text("0");
            $("#indicator-" + indicatorName).css("background", "green");
        }
        
        else {
            
            //update list nav
            $("#li-" + indicatorName + " > #list-count").text(" (" + numError + ")");
            $("#li-" + indicatorName + " > .circle-small").css("background", "#D00000");
            
            //update circle indicator
            $("#indicator-" + indicatorName).text(numError);
            $("#indicator-" + indicatorName).css("background", "#D00000");
        }
    }
});

