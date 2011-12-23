#require 'lemonade'
require 'rgbapng'
require 'ninesixty'

sass_dir = "src"
css_dir = "../context_admin/static/context_admin/stylesheets"
images_dir = "../context_admin/static/context_admin/images"
fonts_dir = "../context_admin/static/context_admin/fonts"

http_path = "/"
http_css_path = "/static/context_admin/stylesheets/"
http_images_path = "/static/context_admin/images/"
http_fonts_path = "/static/context_admin/fonts/"


project_type = :stand_alone
#output_style = :compressed
output_style = :expanded
environment = :production
relative_assets = false
sass_options = {:debug_info => true}

