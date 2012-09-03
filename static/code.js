var TurkGate = {};

function $$(name) {
  return jQuery(document.createElement(name));
}

TurkGate.now = function () {
  return (new Date().getTime()) / 1000;
}

TurkGate.log = function (message) {
  if (typeof console == 'object' && typeof console.log == 'function') {
    console.log(message);
  }
}

TurkGate.urlLink = function (url) {
  var a = document.createElement('a');

  a.href = url;

  return jQuery(a).text(a.pathname == '/' ? a.hostname : a.hostname + a.pathname);
}

TurkGate.zpad = function (n) {
  return (n > 9 ? n.toString() : '0' + n.toString());
}

TurkGate.intval = function (values) {
  return jQuery.map(values, function (value) { return parseInt(value, 10); });
}

TurkGate.datetimeParse = function (value) {
  var datetime = value.split('T');

  var dateints = TurkGate.intval(datetime[0].split('-'));

  var timeints = TurkGate.intval(datetime[1].split('Z')[0].split(':')); // assumes UTC

  var date = new Date();

  date.setUTCFullYear(dateints[0]);
  date.setUTCMonth(dateints[1] - 1);
  date.setUTCDate(dateints[2]);
  date.setUTCHours(timeints[0]);
  date.setUTCMinutes(timeints[1]);
  date.setUTCSeconds(0);

  return date;
}

TurkGate.dateFormat = function (date) {
  var zpad = TurkGate.zpad;

  //var time = [zpad(date.getHours()), zpad(date.getMinutes())].join(':');
  var time = [zpad(date.getHours()), zpad(date.getMinutes()), zpad(date.getSeconds())].join(':');
  var date = [zpad(date.getMonth() + 1), zpad(date.getDate()), date.getFullYear().toString()].join('/');

  return [time, date].join(' ');
}

TurkGate.getParameter = function (name) {
  return unescape(
    (RegExp(name + '=' + '(.+?)(&|$)').exec(location.search)||[,null])[1]
  );
}

TurkGate.Countdown = function (time, element) {
  this.time = time;

  this.element = element;
}

TurkGate.Countdown.prototype.fire = function (fn) {
  this.fire = fn;

  return this;
}

TurkGate.Countdown.prototype.format = function (seconds) {
  var zpad = TurkGate.zpad;

  var m = Math.floor(seconds / 60);

  var h = Math.floor(m / 60);

  m = m - h * 60;

  var s = seconds - (h * 60 * 60) - (m * 60);

  return [zpad(h), zpad(m), zpad(s)].join(':');
}

TurkGate.Countdown.prototype.tick = function () {
  var now = Math.round(new Date().getTime() / 1000);

  if (this.time >= now) {
    this.element.text(this.format(this.time - now));
  } else {
    this.element.text(this.format(0));

    this.fire();
  }
}

TurkGate.JsonPoll = function (url, fn) {
  this.url = url;

  this.fn = fn;

  this.ready = true;
}

TurkGate.JsonPoll.prototype.update = function () {
  if (this.ready) {
    var self = this;

    this.ready = false;

    jQuery.getJSON(this.url, function (data, textStatus, xhr) {
      TurkGate.log('Received ' + xhr.status + ' response from ' + self.url);

      if (xhr.status == 200) {
        self.fn(data);
      }

      self.ready = true;
    });
  }
}

TurkGate.Timer = function (intervalSize, fn) {
  this.intervalID = setInterval(function () { fn(); }, intervalSize);

  this.stop = function () {
    clearInterval(this.intervalID);
  }

  return this;
}

TurkGate.WorkerListItem = function (tbody, worker, now) {
  var tr = $$('tr').appendTo(tbody);

  this.mturkid = $$('td').text(worker.mturkid).appendTo(tr);

  this.remote_addr = $$('td').appendTo(tr);

  this.last_seen = $$('td').appendTo(tr);

  this.assign_id = $$('td').appendTo(tr);

  this.click_go = $$('td').appendTo(tr);

  this.update(worker, now);
}

TurkGate.WorkerListItem.prototype.update = function (worker, now) {
  this.remote_addr.text(worker.remote_addr);

  this.last_seen.text(TurkGate.dateFormat(new Date(worker.last_seen * 1000)));

  if ((now - worker.last_seen) < 10) {
    this.last_seen.addClass('active');
  } else {
    this.last_seen.removeClass('active');
  }

  this.assign_id.text(worker.assignment_id);

  this.click_go.text(worker.click_go ? 'Yes' : 'No');
}

TurkGate.WorkerList = function (parent) {
  var table = $$('table').addClass('worker_list').appendTo(parent);

  var thead = $$('tr').appendTo($$('thead').appendTo(table));

  $$('th').text('Worker ID').appendTo(thead);

  $$('th').text('IP Address').appendTo(thead);

  $$('th').text('Last Seen').appendTo(thead);

  $$('th').text('Assignment ID').appendTo(thead);
  
  $$('th').text('Go?').appendTo(thead);

  this.tbody = $$('tbody').appendTo(table);

  this.items = {};
}

TurkGate.WorkerList.prototype.load = function (data) {
  var self = this;

  var now = TurkGate.now();

  jQuery.each(data.workers, function (index, worker) {
    var item = self.items[worker.mturkid];

    if (item === undefined) {
      self.items[worker.mturkid] = new TurkGate.WorkerListItem(self.tbody, worker, now);
    } else {
      item.update(worker, now);
    }
  });
}

TurkGate.Form = function (element, fields) {
  this.element = element;

  this.fields = fields;

  this.fieldLabels = {};

  for (var i = 0; i < fields.length; i++) {
    var field = fields[i];

    var id = field.name + '_input';

    var div = $$('div').addClass(i > 0 ? 'body' : 'head').appendTo(element);

    this.fieldLabels[field.name] = field.label;

    $$('label').attr('for', id).text(field.label).appendTo(div);

    if (field.type == 'text') {
      var input = $$('input').attr({'type': 'text', 'name': field.name, 'id': id, 'value': field.value, 'class': field.class});

      if (field.full_width !== false) {
        input.addClass('full_width');
      }

      input.attr(field.attrs || {}).appendTo(div);
    } else if (field.type == 'number') {
      $$('input').attr({'type': 'number', 'name': field.name, 'id': id, 'value': field.value, 'size': 16, 'class': field.class}).attr(field.attrs || {}).appendTo(div);
    } else if (field.type == 'textarea') {
      $$('textarea').attr({'name': field.name, 'id': id, 'class': field.class + ' full_width'}).attr(field.attrs || {}).text(field.value).appendTo(div);
    } else if (field.type == 'select') {
      var select = $$('select').attr({'name': field.name, 'id': id, 'class': field.class}).attr(field.attrs || {}).appendTo(div);

      jQuery.each(field.choices, function (_index, choice) {
        $$('option').attr('value', choice.value).text(choice.text).appendTo(select);
      });
    }
  }

  this.controls = $$('div').addClass('foot controls').appendTo(element);

  this.errorDiv = null;

  $$('input').attr('type', 'submit').attr('value', 'Submit').appendTo(this.controls);

  element.find('input:eq(0)').focus();

  var self = this;

  this.element.submit(function (event) {
    self.submit();

    return false;
  });
}

TurkGate.Form.prototype.error = function (message) {
  this.errorDiv = $$('div').addClass('error').text(message).prependTo(this.element);
}

TurkGate.Form.prototype.submitComplete = function (xhr, textStatus) {
  if (textStatus == 'success') {
    window.location = xhr.responseText;
  } else if (textStatus == 'error' && xhr.status == 400) {
    var words = xhr.responseText.split(' ');

    var label = this.fieldLabels[words[0]];

    if (label === undefined) {
      this.error(xhr.responseText);
    } else {
      words[0] = label;

      this.error(words.join(' '));
    }
  } else if (textStatus == 'error' && xhr.status == 500) {
    this.error(xhr.responseText);
  } else {
    // TODO
  }
}

TurkGate.Form.prototype.submit = function () {
  if (this.errorDiv) {
    this.errorDiv.remove();

    this.errorDiv = null;
  }

  var form = this;

  jQuery.ajax({
    url: window.location.href
  , type: 'POST'
  , data: this.element.serialize()
  , dataType: 'text'
  , complete: function (xhr, textStatus) {
      form.submitComplete(xhr, textStatus);
    }
  });
}
