# Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
#
# This file contains all possible options for an identityLookup.conf file.  Use this file to configure 
# Splunk's identity matching properties.
#
# To learn more about configuration files (including precedence) please see the documentation 
# located at http://www.splunk.com/base/Documentation/latest/Admin/Aboutconfigurationfiles
#
# CAUTION:  You can drastically affect your Splunk installation by changing these settings.  
# Consult technical support (http://www.splunk.com/page/submit_issue) if you are not sure how 
# to configure this file.
#

[identityLookup]

match_order = <exact|email|email_short|convention>
   * Comma separated list representing the order by which matches are evaluated.
   * Disabled match types are not evaluated.
   * Defaults to "exact, email, email_short, convention".
     
exact = <1|0>
   * Set whether exact identity matching is enabled or disabled.
   * Exact matches are performed by comparing input value to identity key in Identities Table.
   * Defaults to 1 (enabled).
   
email = <1|0>
   * Set whether email identity matching is enabled or disabled.
   * When enabled, input and email value must match exactly.
   * Equivalent to convention.<n> = email()
   * For example, jsmith@gmail.com == jsmith@gmail.com.
   * Defaults to 1 (enabled).
   
email_short = <1|0>
   * Set whether short email identity matching is enabled.
   * When enabled, email value will be truncated just before '@' symbol and evaluated.
   * For example, jsmith == jsmith@gmail.com.
   * Defaults to 1 (enabled).
   
convention = <1|0>
   * Set whether convention(s) matching is enabled.
   * When enabled, conventions will be evaluated in numerical order.
   * Conventions create additional identity key(s) not specified explicitly in Identities Table.
   * See convention.<n> definitions below.
   * Defaults to 0 (disabled).
   
convention.<n> = <convention>
   * 'n' is a number starting at 0, and increasing by 1 (facilitates multiple conventions)
   * <convention> specified as a combination of columns in the Identities Table
      * <column>(i) represents 'i' number of characters in <column>
      * <column> can be any column in the Identities Table
      * Combine the above representations with characters or strings to define the convention.
   * Collisions are resolved automatically by taking first match in table.  
      * Manual resolution can be achieved by specifying "identity" values for colliding Identities.
   * For example, "John Michael Smith" => first(1)middle(1).last() => jm.smith
   * For example, "Jane Marie Johnson" => first().last() => jane.johnson
   * For example, "John Doe" => ADMIN_first(1)last() => ADMIN_jdoe
   * Defaults to None.
    
case_sensitive = <1|0>
   * For matching methods above, specify whether or not matching is sensitive to case.
   * Defaults to 0 (false).