from boto.mturk.connection import MTurkConnection
from boto.mturk.qualification import Qualifications, \
                                     NumberHitsApprovedRequirement, \
                                     PercentAssignmentsApprovedRequirement,\
                                     PercentAssignmentsSubmittedRequirement,\
                                     PercentAssignmentsReturnedRequirement, \
                                     PercentAssignmentsAbandonedRequirement,\
                                     PercentAssignmentsRejectedRequirement, \
                                     LocaleRequirement
from boto.mturk.question import ExternalQuestion

from datetime import datetime, timedelta
from turktime.helpers import hit_workers

SANDBOX_HOST = 'mechanicalturk.sandbox.amazonaws.com'
HOST = 'mechanicalturk.amazonaws.com'

class Response(object):
  def __init__(self, data):
    self.status = data.status

    if data.status is True:
      self.expiration = data[0].Expiration
      self.creationtime = data[0].CreationTime
      self.identifier = data[0].HITId
      self.HITTypeId = data[0].HITTypeId


def create_hit(href, hit):
  if hit.type == 'MULTIPLE_URLS':  # the max_workers was not set in this form
    hit.max_workers = hit.size1 + hit.size2 + hit.size3 + hit.size4 + hit.size5 + \
                      hit.size6 + hit.size7 + hit.size8 + hit.size9 + hit.size10
  
  
  hostURL = SANDBOX_HOST if hit.sandbox else HOST

  qualifications = Qualifications() 
  if hit.hit_approval > 0 :
    qualifications.add(NumberHitsApprovedRequirement("GreaterThan", hit.hit_approval, False))
  if hit.hit_approval_rate > 0 :
    qualifications.add(PercentAssignmentsApprovedRequirement("GreaterThan", hit.hit_approval_rate, False))
  if hit.accepted_hit_rate > 0 :
    qualifications.add(PercentAssignmentsSubmittedRequirement("GreaterThan", hit.accepted_hit_rate, False))
  if hit.returned_hit_rate > 0 :
    qualifications.add(PercentAssignmentsReturnedRequirement("GreaterThan", hit.returned_hit_rate, False))
  if hit.abandoned_hit_rate > 0 :
    qualifications.add(PercentAssignmentsAbandonedRequirement("LessThan", hit.abandoned_hit_rate, False))
  if hit.rejected_hit_rate > 0 :
    qualifications.add(PercentAssignmentsRejectedRequirement("LessThan", hit.rejected_hit_rate, False))
  if hit.locale_qualification is not None and hit.locale_qualification != 'all' :
    qualifications.add(LocaleRequirement("EqualTo", hit.locale_qualification, False)) 
    
  connection = MTurkConnection(aws_access_key_id=hit.aws_access_key, aws_secret_access_key=hit.aws_secret_key, host=hostURL, is_secure=True)
  
  return Response(connection.create_hit(
    question=ExternalQuestion(href, hit.frame_height)
  , lifetime=hit.lifetime
  , max_assignments=hit.max_workers
  , title=hit.title
  , description=hit.description
  , keywords=['turktime'] # TODO
  , reward=hit.reward
  , duration=hit.duration
  , approval_delay=hit.approval_delay
  , qualifications=qualifications
  , response_groups=['Minimal', 'HITDetail', 'HITQuestion', 'HITAssignmentSummary']
  ))

def cancel_hit(hit):
  hostURL = SANDBOX_HOST if hit.sandbox else HOST

  connection = MTurkConnection(aws_access_key_id=hit.aws_access_key, aws_secret_access_key=hit.aws_secret_key, host=hostURL)

  return connection.disable_hit(hit.mturkid)

def notify(hit):
  hostURL = SANDBOX_HOST if hit.sandbox else HOST

  connection = MTurkConnection(aws_access_key_id=hit.aws_access_key, aws_secret_access_key=hit.aws_secret_key, host=hostURL)

  for worker in hit_workers(hit):
    params = {'WorkerId': worker.mturkid, 'Subject': "It's time to join", 'MessageText': "Hello"}

    connection._process_request('NotifyWorkers', params)

