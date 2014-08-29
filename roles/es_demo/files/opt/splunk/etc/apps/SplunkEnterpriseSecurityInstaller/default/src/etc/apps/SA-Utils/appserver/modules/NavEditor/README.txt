
==========================================================================================
How to use the NavEditor
==========================================================================================

To use the NavEditor, add the module to the view. Then specify the "views_to_edit" parameter to indicate which views you want the editor to display.
 
Views are shown or hidden depending on whether they match one of the entries in the "views_to_edit" parameter. The NavEditor will iterate through each entry and stop on the first entry that matches. The value of the entry indicates if the view that matches ought to be shown ("true" indicates that it ought to be shown, "false" means it won't).

The filter can match wildcards too. This is particularly useful if you want to toggle all views below a collection. The table below indicates what the rules will match on:

	+-----------------------+------------------------------------------------------------------------------------------+
	|         Type          |                                      What to Match                                       |
	+-----------------------+------------------------------------------------------------------------------------------+
	| View                  | The view name (view file name without the extension, e.g. "flashtimeline", not "Search") |
	| Collection            | The collection label                                                                     |
	| Link (a with an href) | The link label (e.g. "Click here" not "http://Splunk.com")                               |
	+-----------------------+------------------------------------------------------------------------------------------+

Generally, you'll want to include a default rule (e.g. such "<param name="*">False</param>") that indicates what must be done with the view that do not match any of the rules. This default rule needs to be after all of the other rules.

Consider the following example:

 1) For the "Search" view with the filename "flashtimeline.xml" the following will show only the search view:
 
  <module name="NavEditor" layoutPanel="panel_row1_col1">
    
    <param name="views_to_edit">
      <list>
        <param name="flashtimeline">True</param>
      </list>
      <list>
      	<param name="*">False</param>
      </list>
    </param>

  </module>
 
 
 2) For the "Click Here" link that goes to "http://Splunk.com" the following will show only the search view:
 
  <module name="NavEditor" layoutPanel="panel_row1_col1">
    
    <param name="views_to_edit">
      <list>
        <param name="Click Here">True</param>
      </list>
      <list>
      	<param name="*">False</param>
      </list>
    </param>

  </module>
  
  
 3) To only show a collection named "Search Stuff":
 
  <module name="NavEditor" layoutPanel="panel_row1_col1">
    
    <param name="views_to_edit">
      <list>
        <param name="Search/*">True</param>
      </list>
      <list>
        <param name="Search">True</param>
      </list>
      <list>
      	<param name="*">False</param>
      </list>
    </param>

  </module>



==========================================================================================
Troubleshooting
==========================================================================================

------------------------------------------------------------------------------------------
I setup the NavEditor but the views shown are not what I expect.
------------------------------------------------------------------------------------------

Here are the likely reasons:

 1) You don't have a default rule
 
    You'll need a default rule to match the items that don't match any of the previous entries. This tell the editor what to do with the items that don't match any of the entries.
 
 2) The rules are in the wrong order
 
    The rules are matched from top to bottom and the editor stops on the first entry that matches. Thus, order matters.
    
    Make sure to separate the entries in separate <list> nodes since items within a <list> node do not maintain order. For example:
    
    Will work:
    
	    <param name="views_to_edit">
	      <list>
	        <param name="Search/*">True</param>
	      </list>
	      <list>
	        <param name="Search">True</param>
	      </list>
	      <list>
	      	<param name="*">False</param>
	      </list>
	    </param>
	    
	May not work:
	
	    <param name="views_to_edit">
	      <list>
	        <param name="Search">True</param>
	        <param name="Search/*">True</param>
	      	<param name="*">False</param>
	      </list>
	    </param>
    
 
 3) The thing to match on is incorrect
 
    The views are matched on the name (the filename) not the label. Otherwise, the label is used.
 
 4) You have a rule to match the collection or the items within the collection, but not both

    You'll need two entries to show a collection and all items within the collection. One will show the items under the collection (like "Search/*") and another to show the collection itself (like "Search")/
    