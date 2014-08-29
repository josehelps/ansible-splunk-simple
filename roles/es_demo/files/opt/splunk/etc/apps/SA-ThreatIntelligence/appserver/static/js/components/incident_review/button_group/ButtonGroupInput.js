define(function(require) {
    var BaseInput = require('splunkjs/mvc/simpleform/input/base');
    var ButtonGroupView = require('app-components/incident_review/button_group/ButtonGroupView');
    var FormUtils = require('splunkjs/mvc/simpleform/formutils');

    FormUtils.registerInputType('button', ButtonGroupView, { choices: true, multiValue: true }); 

    var ButtonGroupInput = BaseInput.extend({
        initialVisualization: 'button'
    }); 

    return ButtonGroupInput;
});
