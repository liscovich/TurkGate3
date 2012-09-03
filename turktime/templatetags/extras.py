from google.appengine.ext import webapp

register = webapp.template.create_template_register()

def get_range(value, offset=0):
  try:
    offset = int(offset)
  except Exception:
    offset = 0

  return range(value)[offset:]
register.filter(get_range)

from turktime.helpers import get_location
register.filter(get_location)

