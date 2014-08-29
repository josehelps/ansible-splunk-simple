define (['splunk.util'], function(SplunkUtil) {
	var irUtils = {
			/*
			 * Perform dynamic field replacement inside the provide field value
			 * @param object eventModel : event: <models.services.search.job.ResultsV2.result[i]> to get other field values
			 * @param string field : field value which requires dynamic field replacement init
			 */
			getFieldValue : function(eventModel, field) {
				// _raw field no field replacement
				if (field === "_raw") {
					return field;
				}
				var regEx = /\$(\w+)\$/g;
				// get field and replace it
				var insideField = null;
				var modifiedVal = field;
				while((insideField = regEx.exec(field)) !== null) {
					if(eventModel.has(insideField[1])) {
						var value = SplunkUtil.fieldListToString(eventModel.get(insideField[1]));
						modifiedVal = modifiedVal.replace(insideField[0], value);
					} else {
						// TODO: unknown (review with UX)
						modifiedVal = modifiedVal.replace(insideField[0], "unknown");
					}
				}
				return modifiedVal;
			},

			/*
			 * Check raw (orig_raw) data value
			 */
			isRawNasty : function(raw) {
				var newLineRegEx = /([\r\n]+)/g;
				var lines = 0;
				while(newLineRegEx.test(raw)) {
					lines = lines + 1;
				}
				var nastyRegEx = /([^\s]{55})/g;
				var nastyMatch = nastyRegEx.test(raw);
				if (lines <= 1 && raw.length > 600) {
					return true;
				} else if(nastyMatch) {
					return true;
				} else {
					return false;
				}
			},
			
			/*
			 * Convert First Char to upper case
			 */
			convertFirstCharToUpperCase: function(str) {
				return str && str.charAt(0).toUpperCase() + str.substring(1);
			}
	};
	return irUtils;
});