"""Middleware for handling static files with better caching."""
import os
import re
import time
from flask import send_file

class StaticFileMiddleware:
    """WSGI middleware for serving static files with better caching."""
    
    def __init__(self, app, static_folder, cache_timeout=86400):
        self.app = app
        self.static_folder = static_folder
        self.cache_timeout = cache_timeout
        
        # File types and their associated cache timeouts
        self.cache_timeouts = {
            # CSS and JS files: 1 day
            r'\.css$': 86400,
            r'\.js$': 86400,
            # Images: 7 days
            r'\.(jpg|jpeg|png|gif|ico|svg)$': 7 * 86400,
            # Fonts: 30 days
            r'\.(woff|woff2|ttf|eot)$': 30 * 86400,
        }
    
    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        
        # Check if this is a request for a static file
        if path.startswith('/static/'):
            file_path = os.path.join(
                self.static_folder, 
                path.replace('/static/', '', 1)
            )
            
            # Check if file exists
            if os.path.isfile(file_path):
                return self.serve_static(environ, start_response, file_path, path)
        
        # Not a static file, let the app handle it
        return self.app(environ, start_response)
    
    def serve_static(self, environ, start_response, file_path, path):
        """Serve a static file with appropriate caching headers."""

        # Get last modified time and file size
        mtime = os.path.getmtime(file_path)
        file_size = os.path.getsize(file_path)
        mtime_str = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(mtime))

        # Set timeout based on file type
        timeout = self.cache_timeout
        for pattern, pattern_timeout in self.cache_timeouts.items():
            if re.search(pattern, path, re.IGNORECASE):
                timeout = pattern_timeout
                break

        # Check if file has been modified
        if_modified_since = environ.get('HTTP_IF_MODIFIED_SINCE')
        if if_modified_since and if_modified_since == mtime_str:
            # Return 304 Not Modified
            headers = [
                ('Date', time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())),
                ('Content-Type', self._get_content_type(path)),
                ('Cache-Control', f'public, max-age={timeout}'),
                ('Last-Modified', mtime_str),
            ]
            start_response('304 Not Modified', headers)
            return []

        # Return the file with caching headers
        headers = [
            ('Content-Type', self._get_content_type(path)),
            ('Cache-Control', f'public, max-age={timeout}'),
            ('Last-Modified', mtime_str),
            ('Content-Length', str(file_size)),
        ]

        start_response('200 OK', headers)

        # For small files (less than 64KB), just return the file content directly
        if file_size < 65536:
            try:
                with open(file_path, 'rb') as f:
                    return [f.read()]
            except Exception as e:
                # Log error and return empty response on file read error
                import logging
                logging.error(f"Error reading static file {file_path}: {str(e)}")
                return [b'']

        # For larger files, create a proper WSGI generator to ensure file closure
        def file_generator(environ, start_response):
            # The start_response has already been called in the serve_static method
            # We just need to return a generator that yields chunks of file content
            try:
                with open(file_path, 'rb') as f:
                    chunk_size = 8192
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk
            except Exception as e:
                # Log error on file read error
                import logging
                logging.error(f"Error streaming static file {file_path}: {str(e)}")
                yield b''

        # Create a generator function that will be returned and called by the WSGI server
        def wsgi_application(environ, start_response):
            # Return the generator
            return file_generator(environ, start_response)

        # Return the callable WSGI application, not the generator directly
        return wsgi_application
    
    def _get_content_type(self, path):
        """Get the content type based on file extension."""
        ext = os.path.splitext(path)[1].lower()
        content_types = {
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.ico': 'image/x-icon',
            '.svg': 'image/svg+xml',
            '.woff': 'font/woff',
            '.woff2': 'font/woff2',
            '.ttf': 'font/ttf',
            '.eot': 'application/vnd.ms-fontobject',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.pdf': 'application/pdf',
            '.zip': 'application/zip',
            '.mp3': 'audio/mpeg',
            '.mp4': 'video/mp4',
            '.webp': 'image/webp',
            '.otf': 'font/otf',
        }
        return content_types.get(ext, 'application/octet-stream')