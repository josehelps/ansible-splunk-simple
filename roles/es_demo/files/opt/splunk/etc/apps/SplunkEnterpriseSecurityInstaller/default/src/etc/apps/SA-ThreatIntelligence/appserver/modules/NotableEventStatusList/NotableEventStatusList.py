import logging

import cherrypy
import splunk.bundle as bundle

import splunk.admin as admin
import splunk.entity as en

logger = logging.getLogger('splunk.appserver.SA-ThreatIntelligence.modules.NotableEventStatusList')

class Page:
    """
    Represents a page in the paginator.
    """
    
    def __init__(self, page_number, offset, is_current_page=False, is_prev=False, is_next=False):
        self.page_number = page_number
        self.is_current_page = is_current_page
        self.is_prev = is_prev
        self.is_next = is_next
        self.offset = offset
        
    def __str__(self):
        return str(self.page_number)

class Paginator:
    """
    Provides a mechanism for computed pagination 
    """
    
    def __init__(self, total_entries, offset, entries_per_page, add_prev_next=True):    
        self.total_entries = total_entries
        self.offset = offset
        self.entries_per_page = entries_per_page
        
        self.end_offset_current_page = self.__end_offset_current_page__()
        self.__populate_pages__(add_prev_next)
        
    def get_page_contents(self, items):
        """
        Get the items for the given page from the given array
        """
        
        return items[self.offset : self.offset + self.entries_per_page ]
    
    def __populate_pages__(self, add_prev_next=True):
        """
        Populate an internal data structure that will contain the pages to be displayed.
        """
        self.pages = []
        
        # Add the previous button
        if add_prev_next and self.has_previous():
            self.pages.append( Page( "Previous", 0, False, is_prev=True) )
        
        # Add the pages
        for page_num in range(0, self.pages_count() ):
            
            page_offset = page_num * self.entries_per_page
            
            if page_offset == self.offset:
                self.pages.append( Page(page_num + 1, page_offset, True) )
            else:
                self.pages.append( Page(page_num + 1, page_offset, False) )
                
        # Add the next button
        if add_prev_next and self.has_next():
            self.pages.append( Page( "Next", self.last_offset(), False, is_next=True) )
        
    def __end_offset_current_page__(self):
        """
        Provides the end offset in the current page
        """
        
        last_in_offset = self.offset + (self.entries_per_page - 1)
        
        if last_in_offset > (self.total_entries - 1):
            return self.total_entries - 1
        else:
            return last_in_offset
        
    def last_offset(self):
        """
        Get the offset value of the last number
        """
        
        return (self.pages_count() - 1) * self.entries_per_page
        
    def pages_count(self):
        """
        Get the number of pages  (not including the previous and next links)
        """
        
        pages_num = (self.total_entries * 1.0) / self.entries_per_page
        
        pages_num = math.ceil(pages_num)
        
        return int(pages_num)
    
    def has_previous(self):
        """
        Determine if a previous page exists.
        """
        
        if self.offset > 0:
            return True
        else:
            return False
    
    def has_next(self):
        """
        Determine if a next page exists
        """
        
        if (self.offset + self.entries_per_page) >= self.total_entries:
            return False
        else:
            return True
    
    def previous_offset(self):
        """
        Get the offset value for the previous page. Returns the current if alread at the current page.
        """
        
        prev_offset = self.offset - entries_per_page
        
        if prev_offset < 0:
            return 0
        else:
            return prev_offset
    
    def __iter__(self):
        return self.pages.__iter__()
    
    def __getitem__(self, key):
        return self.pages[key]
    
    def __len__(self):
        return self.pages.__len__()

class NoSessionKeyException(Exception):
    """
    To be thrown if we could not get a session key
    """
    pass


