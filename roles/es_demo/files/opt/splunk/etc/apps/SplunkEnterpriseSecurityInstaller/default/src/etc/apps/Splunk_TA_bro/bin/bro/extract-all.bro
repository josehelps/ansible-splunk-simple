# Process packets despite bad checksums.
redef ignore_checksums = T;

# Extract everything !
redef IRC::extract_file_types = /.*/;
redef FTP::extract_file_types = /.*/;
redef HTTP::extract_file_types = /.*/;
redef SMTP::extract_file_types = /.*/;

# Tweak SMTP excerpt length.
redef SMTP::default_entity_excerpt_len = 0; #1024;

# Disable password logging
redef FTP::default_capture_password = F;
redef HTTP::default_capture_password = F;

# Log HTTP server header names
@load protocols/http/header-names
redef HTTP::log_server_header_names = T;

