require(["jquery", "splunkjs/mvc", "splunkjs/mvc/simplexml/ready!"], function($, mvc) {
    var headerView = mvc.Components.get("header");
    headerView.settings.set("appbar", false);
    headerView.render();
});

