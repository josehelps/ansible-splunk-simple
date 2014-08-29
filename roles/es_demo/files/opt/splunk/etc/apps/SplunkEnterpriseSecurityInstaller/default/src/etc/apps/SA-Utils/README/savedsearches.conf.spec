
[<stanza name>]

## Each collection should be assigned a unique integer per view "<n>"

## The per-view collection name
display.page.<view_name>.<n>.collection_name = <string>

## The per-view per-collection title of the swim lane
display.page.<view_name>.<n>.title           = <string>

## The per-view per-collection color of the swim lane
display.page.<view_name>.<n>.color           = [blue,red,orange,yellow,purple,green]

## The per-view per-collection view to forward the user to when they click the value
display.page.<view_name>.<n>.drilldown_uri   = <string>

## The per-view per-collection order of the swimlane
## This is an arbitrary integer starting at 0 (integers should not overlap)
## If group order overlaps with another swim lane they will be ordered alphanumerically
display.page.<view_name>.<n>.order           = <integer>