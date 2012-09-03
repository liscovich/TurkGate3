from google.appengine.ext import db as datastore

from turktime.models import Worker

import time, hmac


def datetime_format(t):
  return '%04d-%02d-%02dT%02d:%02dZ' % (t.year, t.month, t.day, t.hour, t.minute)


def unix_timestamp(datetime):
  if datetime:
    return int(time.mktime(datetime.timetuple()))
  else:
    return None


def hit_workers(hit):
  return Worker.all().filter('hit = ', hit)


def hit_group_url(hit):
  if hit.sandbox:
    return 'https://workersandbox.mturk.com/mturk/preview?groupId=' + hit.groupid
  else:
    return 'https://www.mturk.com/mturk/preview?groupId=' + hit.groupid


def worker_lookup(hit, mturkid):
  return hit_workers(hit).filter('mturkid = ', mturkid).get()


def next_worker_number_increment(hit_key):
  hit = datastore.get(hit_key)
  num = hit.next_worker_number
  hit.next_worker_number += 1
  hit.put()
  return num


def next_worker_number(hit):
  return datastore.run_in_transaction(next_worker_number_increment, hit.key())


def get_sizes(hit):
    sizes = []
    sizes.append(0)
    sizes.append(sizes[0] + hit.size1)
    sizes.append(sizes[1] + hit.size2)
    sizes.append(sizes[2] + hit.size3)
    sizes.append(sizes[3] + hit.size4)
    sizes.append(sizes[4] + hit.size5)
    sizes.append(sizes[5] + hit.size6)
    sizes.append(sizes[6] + hit.size7)
    sizes.append(sizes[7] + hit.size8)
    sizes.append(sizes[8] + hit.size9)
    sizes.append(sizes[9] + hit.size10)
    sizes.append(10**9)  # infinite
    return sizes


def get_location(hit, i=0):
  try:
    i = int(i)
  except Exception:
    i = 0

  if i <= 0:
    return hit.location
  elif 1 <= i <= 10:
    try:
      return eval('hit.location%d' % i)
    except:
      return ''
  else:
    return hit.location10


def target_url(hit, query_string, worker):
  params = '%s&workerNumber=%d' % (query_string, worker.number)

  if hit.auth_secret:
    params = params + '&auth=' + hmac.new(hit.auth_secret, str(worker.number)).hexdigest()

  if hit.type == 'MULTIPLE_URLS':
    sizes = get_sizes(hit)
    segment = 0
    for i in range (0, 11):
      if sizes[i] < worker.number <= sizes[i + 1]:
        segment = i
        break
    location = get_location(hit, segment + 1)
  else:
    location = hit.location
    
  if location.find('?') < 0:
    return '%s?%s' % (location, params)
  else:
    return '%s&%s' % (location, params)
