from google.appengine.api import users
from google.appengine.api import mail
from google.appengine.api import urlfetch
from google.appengine.api.labs.taskqueue import Task
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app as run_wsgi
from google.appengine.ext.db import BadKeyError

from turktime.mturk import create_hit, cancel_hit, notify
from turktime.models import HIT, Worker
from turktime.helpers import unix_timestamp, datetime_format, target_url, hit_group_url, get_sizes
from turktime.helpers import hit_workers, worker_lookup, next_worker_number

from datetime import datetime, timedelta

from boto.exception import BotoClientError, BotoServerError

from pyiso8601 import iso8601

from django.utils import simplejson as json

import re, logging


class Link(object):
  def __init__(self, href, text):
    self.href = href
    self.text = text


class BadValueError(Exception):
  def __init__(self, reason):
    self.reason = reason


class RequestHandler(webapp.RequestHandler):
  def render(self, path, params):
    self.response.out.write(template.render(path, params))

  def json(self, data):
    self.response.headers.add_header('Content-Type', 'application/json')

    self.response.out.write(json.dumps(data))

  def not_found(self):
    self.error(404)

  def hit_url(self, hit, path_suffix=None):
    url = '%s/hit/%s' % (self.request.host_url, str(hit.key()))

    if path_suffix is None:
      return url
    else:
      return url + str(path_suffix)

  def hit_link(self, hit):
    return Link(self.hit_url(hit), hit.title)

  def hit_countdown_url(self, hit):
    return self.hit_url(hit, '/countdown')

  def hit_heartbeat_url(self, hit):
    return self.hit_url(hit, '/heartbeat')

  def hit_location_url(self, hit):
    return self.hit_url(hit, '/location')

  def hit_workers_url(self, hit):
    return self.hit_url(hit, '/workers.json')

  def hit_cancel_url(self, hit):
    return self.hit_url(hit, '/cancel.json')

  def worker_click_go(self, worker):
    return '/clickgo/%s' % str(worker.key())

  def get_value(self, key, required=True, mapfn=None):
    value = self.request.get(key).strip()

    if len(value) > 0:
      if mapfn is None:
        return value
      else:
        return mapfn(value)
    else:
      if required:
        raise BadValueError('%s is required' % key)
      else:
        return None

  def map_type(self, type):
    """
    Map to values set in datastore
    Return MULTIPLE_URLS, FOCAL_TIME, PASS_THROUGH or NORMAL
    """
    if type == 'urls':
      return 'MULTIPLE_URLS'
    elif type == 'time':
      return 'FOCAL_TIME'
    elif type == 'pass':
      return 'PASS_THROUGH'
    else:
      return 'NORMAL'


class Root(RequestHandler):
  def get(self):
    self.redirect('/hits')

class HitList(RequestHandler):
  def get(self):
    user = users.get_current_user()
    type = self.get_value('type', required=False)
    type = self.map_type(type)

    self.render('priv/hit_list.html', {'user': user, 'type': type, 'time': datetime_format(datetime.utcnow())})

  def post(self):

    type = self.get_value('type', required=False)
    type = self.map_type(type)

    try:
      hit = HIT()
      hit.owner = users.get_current_user()
      hit.lifetime = self.get_value('lifetime', required=True, mapfn=int)
      hit.duration = self.get_value('duration', required=True, mapfn=int)
      hit.approval_delay = self.get_value('approval_delay', required=True, mapfn=int)
      
      hit.hit_approval = self.get_value('hit_approval', required=False, mapfn=int)
      hit.hit_approval_rate = self.get_value('hit_approval_rate', required=True, mapfn=int)
      hit.accepted_hit_rate = self.get_value('accepted_hit_rate', required=True, mapfn=int)
      hit.returned_hit_rate = self.get_value('returned_hit_rate', required=True, mapfn=int)
      hit.abandoned_hit_rate = self.get_value('abandoned_hit_rate', required=True, mapfn=int)
      hit.rejected_hit_rate = self.get_value('rejected_hit_rate', required=True, mapfn=int)
      hit.locale_qualification = self.get_value('locale_qualification', required=True)
      
      hit.frame_height = self.get_value('frame_height', required=True, mapfn=int)
  
      if type != 'MULTIPLE_URLS':
        hit.max_workers = self.get_value('max_workers', required=True, mapfn=int)
        if type != 'PASS_THROUGH':
          hit.min_workers = self.get_value('min_workers', required=True, mapfn=int)

      if type == 'MULTIPLE_URLS':
        hit.location1 = self.get_value('location1', required=True)
        hit.size1 = self.get_value('size1', required=True, mapfn=int)
        hit.location2 = self.get_value('location2', required=False)
        hit.size2 = self.get_value('size2', required=False, mapfn=int)
        hit.location3 = self.get_value('location3', required=False)
        hit.size3 = self.get_value('size3', required=False, mapfn=int)
        hit.location4 = self.get_value('location4', required=False)
        hit.size4 = self.get_value('size4', required=False, mapfn=int)
        hit.location5 = self.get_value('location5', required=False)
        hit.size5 = self.get_value('size5', required=False, mapfn=int)
        hit.location6 = self.get_value('location6', required=False)
        hit.size6 = self.get_value('size6', required=False, mapfn=int)
        hit.location7 = self.get_value('location7', required=False)
        hit.size7 = self.get_value('size7', required=False, mapfn=int)
        hit.location8 = self.get_value('location8', required=False)
        hit.size8 = self.get_value('size8', required=False, mapfn=int)
        hit.location9 = self.get_value('location9', required=False)
        hit.size9 = self.get_value('size9', required=False, mapfn=int)
        hit.location10 = self.get_value('location10', required=False)
        hit.size10 = self.get_value('size10', required=False, mapfn=int)
      else:
        hit.location = self.get_value('location', required=True)

      hit.aws_access_key = self.get_value('aws_access_key', required=True)
      hit.aws_secret_key = self.get_value('aws_secret_key', required=True)
      hit.auth_secret = self.get_value('auth_secret', required=False)
      hit.title = self.get_value('title', required=True)
      hit.description = self.get_value('description', required=True)
      hit.reward = self.get_value('reward', required=True)
      hit.handle_submit = self.get_value('handle_submit', required=False, mapfn=bool)
      hit.always_pay = self.get_value('always_pay', required=False, mapfn=bool)
      hit.sandbox = self.get_value('sandbox', required=False, mapfn=bool)
      hit.blacklist = re.split('[,\s]+', self.request.get('blacklist').strip())
      hit.info = self.get_value('info')

      if type == 'FOCAL_TIME':
        hit.focal_time = iso8601.parse_date(self.get_value('focal_time', required=True).replace('Z', ':00Z'))

      hit.type = type
      hit.next_worker_number = 1
      hit.put()
    except BadValueError, error:
      self.response.set_status(400)
      self.response.out.write(error.reason)
      return

    try:
      response = create_hit(self.hit_countdown_url(hit), hit)

      hit.mturkid = response.identifier
      hit.groupid = response.HITTypeId
      hit.time = iso8601.parse_date(response.expiration)
      hit.put()

      if type == 'FOCAL_TIME':
        task = Task(url='/notification', params={'key': str(hit.key())},
                    eta=hit.focal_time - timedelta(minutes=2))
        task.add('default')

      self.response.out.write(self.hit_url(hit))
    except (BotoClientError, BotoServerError), aws:
      error = 'Error: %s: %s' % (aws.errors[0][0], aws.errors[0][1])

      self.response.set_status(500)
      self.response.out.write(error)


class HitListJson(RequestHandler):
  def item(self, hit):
    return {
      'url': self.hit_url(hit)
    , 'title': hit.title
    , 'location': hit.location
    , 'time': unix_timestamp(hit.time)
    , 'key': str(hit.key())
    , 'added': datetime_format(hit.added)
    }

  def get(self):
    type = self.get_value('type', required=False)
    type = self.map_type(type)
    hits = HIT.all().filter('owner = ', users.get_current_user()) \
                    .filter('type = ', type)\
                    .order('added')

    data = [self.item(hit) for hit in hits]

    self.json(data)


class HitDetailJson(RequestHandler):
  def item(self, hit):
    return {
      'lifetime': hit.lifetime,
      'duration': hit.duration,
      'approval_delay': hit.approval_delay,
      'hit_approval': hit.hit_approval,
      'hit_approval_rate': hit.hit_approval_rate,
      'accepted_hit_rate' : hit.accepted_hit_rate,
      'returned_hit_rate' : hit.returned_hit_rate,
      'abandoned_hit_rate': hit.abandoned_hit_rate,
      'rejected_hit_rate':  hit.rejected_hit_rate,
      'locale_qualification':  hit.locale_qualification,
      
      'frame_height': hit.frame_height ,
      'max_workers': hit.max_workers,
      'min_workers': hit.min_workers,
      'location': hit.location,
      'location1': hit.location1,
      'size1': hit.size1,
      'location2': hit.location2,
      'size2': hit.size2,
      'location3': hit.location3,
      'size3': hit.size3,
      'location4': hit.location4,
      'size4': hit.size4,
      'location5': hit.location5,
      'size5': hit.size5,
      'location6': hit.location6,
      'size6': hit.size6,
      'location7': hit.location7,
      'size7': hit.size7,
      'location8': hit.location8,
      'size8': hit.size8,
      'location9': hit.location9,
      'size9': hit.size9,
      'location10': hit.location10,
      'size10': hit.size10,
      'aws_access_key': hit.aws_access_key,
      'aws_secret_key': hit.aws_secret_key,
      'auth_secret': hit.auth_secret,
      'title': hit.title,
      'description': hit.description,
      'reward': hit.reward,
      'handle_submit': "true" if hit.handle_submit else "",
      'always_pay': "true" if hit.always_pay else "",
      'sandbox': "true" if hit.sandbox else "",
      'blacklist': ', '.join(hit.blacklist),
      'info': hit.info
    }

  def get(self, key):
    try:
      hit = HIT.get(key)
    except BadKeyError:
      data = {}
    else:
      data = self.item(hit)

    self.json(data)


class HitDetail(RequestHandler):
  def get(self, key):
    hit = HIT.get(key)

    if hit:
      if hit.focal_time:
        focal_time = datetime_format(hit.focal_time)
      else:
        focal_time = None

      self.render('priv/hit_detail.html', {
        'hit': hit
      , 'hit_group_url': hit_group_url(hit)
      , 'added': datetime_format(hit.added)
      , 'timestamp': json.dumps(unix_timestamp(hit.time))
      , 'workers_url': json.dumps(self.hit_workers_url(hit))
      , 'cancel_url': json.dumps(self.hit_cancel_url(hit))
      , 'user': users.get_current_user()
      , 'focal_time': focal_time
      })
    else:
      self.not_found()


class HitWorkerJson(RequestHandler):
  def get(self, key):
    hit = HIT.get(key)

    if hit:
      workers = []

      for worker in hit_workers(hit):
        workers.append({
          'last_seen': unix_timestamp(worker.last_seen)
        , 'remote_addr': worker.remote_addr
        , 'mturkid': worker.mturkid
        , 'assignment_id': worker.assignment_id
        , 'click_go': worker.click_go
        })

      self.json({'workers': workers})
    else:
      self.not_found()


class HitCountdown(RequestHandler):
  def get(self, key):
    hit = HIT.get(key)

    if hit:
      if self.request.get('assignmentId') != 'ASSIGNMENT_ID_NOT_AVAILABLE':
        if self.request.get('workerId') in hit.blacklist:
          self.render('priv/hit_blacklisted.html', {'title': hit.title})
          return

        worker = worker_lookup(hit, self.request.get('workerId'))

        if worker is None:
          worker = Worker()
          worker.hit = hit
          worker.mturkid = self.request.get('workerId')
          worker.assignment_id = self.request.get('assignmentId')
          worker.number = next_worker_number(hit)  # save number ASAP

        worker.remote_addr = self.request.remote_addr
        worker.user_agent = self.request.headers['User-Agent']
        worker.put()
      
        clickgo_url = json.dumps(self.worker_click_go(worker))

      else:
        clickgo_url = json.dumps('')

      self.render('priv/hit_countdown.html', {
        'time': unix_timestamp(hit.time)
      , 'title': hit.title
      , 'heartbeat_url': json.dumps(self.hit_heartbeat_url(hit))
      , 'location_url': json.dumps(self.hit_location_url(hit))
      , 'info': hit.info
      , 'hit': hit
      , 'clickgo_url': clickgo_url
      })
    else:
      self.not_found()


class HitHeartbeat(RequestHandler):
  def get(self, key):
    hit = HIT.get(key)

    if hit:
      worker = worker_lookup(hit, self.request.get('workerId'))

      if worker is None:
        self.not_found()
      else:
        worker.remote_addr = self.request.remote_addr
        worker.user_agent = self.request.headers['User-Agent']
        worker.put()

        if hit.type == 'MULTIPLE_URLS':
          sizes = get_sizes(hit)
          remaining = 0
          for i in range (0, 11):
            if sizes[i] < worker.number <= sizes[i + 1]:
              remaining = sizes[i + 1] - worker.number
              break
          self.json({'status': 'OK', 'remaining': str(remaining)})
        elif hit.type == 'PASS_THROUGH':
          self.json({'status': 'OK', 'go': 'true'})
        else:
          self.json({'status': 'OK'})
    else:
      self.not_found()


class HitLocation(RequestHandler):
  def get(self, key):
    hit = HIT.get(key)

    # TODO: track worker details here too?

    if hit:
      if hit.type == 'PASS_THROUGH' or datetime.utcnow() > hit.time:  # don't check time for pass-through
        worker = worker_lookup(hit, self.request.get('workerId'))

        if worker is None:
          self.not_found() # TODO: log error?
        else:
          if hit.min_workers > hit_workers(hit).count(): # TODO: only include active workers in count?
            if hit.always_pay:
              self.json({'available': False, 'message': 'Not enough people. You will still be paid for this HIT.', 'submit': True})
            else:
              self.json({'available': False, 'message': 'Not enough people. Please return this HIT.', 'submit': False})
          else:
            #worker.number = next_worker_number(hit)
            #worker.put()

            url = target_url(hit, self.request.query_string, worker)

            self.json({'available': True, 'location': url, 'submit': hit.handle_submit})
      else:
        self.not_found() # or other error code?
    else:
      self.not_found()


class HitCancelJson(RequestHandler):
  def get(self, key):
    hit = HIT.get(key)

    if hit:
      try: 
        cancel_hit(hit)
      except Exception:
        status = 'NG'
      else:
        hit.delete()
        status = 'OK'

      self.json({'status': status})
    else:
      self.not_found()


class DateTimeJson(RequestHandler):
  def get(self):
    self.json(datetime_format(datetime.utcnow()))


class Notification(RequestHandler):
  def post(self):
    key = self.request.get('key')
    logging.info("key=" + key)
    hit = HIT.get(key)
    notify(hit)


class ClickGoJson(RequestHandler):
  def get(self, key):
    worker = Worker.get(key)

    if worker:
      if not worker.click_go:
        worker.click_go = True
        worker.put()

      self.json({'status': 'OK'})
    else:
      self.json({'status': 'NG'})


def handlers():
  return [
    ('/', Root)
  , ('/hit/([^/]+)', HitDetail)
  , ('/hit/([^/]+)/countdown', HitCountdown)
  , ('/hit/([^/]+)/heartbeat', HitHeartbeat)
  , ('/hit/([^/]+)/location', HitLocation)
  , ('/hit/([^/]+)/cancel.json', HitCancelJson)
  , ('/hit/([^/]+)/workers.json', HitWorkerJson)
  , ('/hit/([^/]+)/detail.json', HitDetailJson)
  , ('/hits', HitList)
  , ('/hits.json', HitListJson)
  , ('/datetime.json', DateTimeJson)
  , ('/notification', Notification)
  , ('/clickgo/([^/]+)', ClickGoJson)
  ]


def application():
  return webapp.WSGIApplication(handlers(), debug=True)


def main():
  run_wsgi(application())

webapp.template.register_template_library('turktime.templatetags.extras')

if __name__ == '__main__':
  main()
