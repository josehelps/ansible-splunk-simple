
[keyindicator]

## The title of the metric
title           = <string>

## The sub title of the metric
subtitle        = <string>

## The field that contains the value to be displayed
## This is a field name (case-sensitive)
value           = <string>

## This field specifies text to to be included after the value (e.g. "%")
value_suffix    = <string>

## The threshold for which the item should be considered a warning (to turn the text red) 
threshold       = <integer>

## The field that contains the delta to be displayed
## This is a field name (case-sensitive)
delta           = <string>

## A view to forward the user to when they click the value
drilldown_uri   = <string>

## By default, an increase will be assumed to be bad. Setting invert to true makes the module make increases green instead of red. 
invert          = 1 | 0

## An iterable group double (group name and group order)
## This allows one to assign a keyindicator to one or more groups
## As well as to specify the order of that indicator within the group

## This is an arbitrary string
group.<n>.name  = <string>

## This is an arbitrary integer (integers should not overlap)
## If group order overlaps with another keyindicator they will be ordered alphanumerically
group.<n>.order = <integer>


[swimlane]

## The title of the swim lane
title             = <string>

## The color of the swim lane
color             = [blue,red,orange,yellow,purple,green]

## The mothod used to build the swimlane constraints
## reverse_asset and reverse_identity require SA-IdentityManagement
## string method simple uses the constraint_fields and the specified value to build $constraints$
constraint_method = [reverse_asset_lookup,reverse_identity_lookup,string]

## The field(s) used to build the swimlane constraints
## If specifying reverse_asset method, only following constraint_fields are allowed: ['src', 'dest', 'dvc', 'host', 'orig_host']
## If specifying reverse_identity method, only the following constraint_fields are allowed: ['user', 'src_user']
## The above fields may be specified with data model lineage (i.e. Authentication.src, All_Changes.user, etc.)
constraint_fields = <comma-delimited-field-list>

## A search to forward the user to when they select swim lane objects
drilldown_search     = <string>
