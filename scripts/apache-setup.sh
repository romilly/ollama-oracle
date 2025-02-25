#!/bin/bash
# Apache Setup for PDF Document Server on Raspberry Pi

# Update package lists and install Apache
sudo apt update
sudo apt install -y apache2

# Create a directory for your documents (if needed)
# Or you can use an existing directory where your PDFs are already stored
# sudo mkdir -p /var/www/documents

# Optional: Copy your existing PDFs to the web directory
# If your PDFs are already in a specific directory, you can symlink it instead
# sudo cp -r /path/to/your/pdfs/* /var/www/documents/
# OR create a symlink:
# sudo ln -s /path/to/your/pdfs /var/www/documents

# Create Apache virtual host configuration
sudo tee /etc/apache2/sites-available/documents.conf > /dev/null << 'EOL'
<VirtualHost *:80>
    ServerAdmin webmaster@localhost
    DocumentRoot /var/www/documents
    
    <Directory /var/www/documents>
        Options Indexes FollowSymLinks
        AllowOverride None
        Require all granted
        
        # PDF File handling
        AddType application/pdf .pdf
        
        # Improve directory listing
        IndexOptions FancyIndexing HTMLTable VersionSort SuppressDescription FoldersFirst SuppressIcon
        
        # Show specific file types at the top
        IndexOrderDefault Descending Name
        
        # Example of custom header/footer (optional)
        # HeaderName HEADER.html
        # ReadmeName README.html
    </Directory>
    
    ErrorLog ${APACHE_LOG_DIR}/documents_error.log
    CustomLog ${APACHE_LOG_DIR}/documents_access.log combined
</VirtualHost>
EOL

# Enable the site and necessary modules
sudo a2ensite documents.conf
sudo a2enmod autoindex
sudo a2dissite 000-default.conf

# Set the correct permissions
sudo chown -R www-data:www-data /var/www/documents
sudo chmod -R 755 /var/www/documents

# Restart Apache to apply changes
sudo systemctl restart apache2

# Check status to make sure everything is running
sudo systemctl status apache2

# Note: If you have your files in a different location, replace /var/www/documents
# with your actual path and update the configuration accordingly.

echo "Setup completed! Your document server should be running at http://YOUR_PI_IP"
