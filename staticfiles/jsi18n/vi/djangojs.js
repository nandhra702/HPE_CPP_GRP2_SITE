

'use strict';
{
  const globals = this;
  const django = globals.django || (globals.django = {});

  
  django.pluralidx = function(n) {
    const v = 0;
    if (typeof v === 'boolean') {
      return v ? 1 : 0;
    } else {
      return v;
    }
  };
  

  /* gettext library */

  django.catalog = django.catalog || {};
  
  const newcatalog = {
    "%(cnt)d submission in %(year)d": [
      "%(cnt)d b\u00e0i g\u1eedi trong n\u0103m %(year)d"
    ],
    "%(cnt)d submission in the last year": [
      "%(cnt)d b\u00e0i g\u1eedi trong m\u1ed9t n\u0103m tr\u01b0\u1edbc"
    ],
    "%(cnt)d submission on %(date)s": [
      "%(cnt)d b\u00e0i g\u1eedi trong ng\u00e0y %(date)s"
    ],
    "%(cnt)d total submission": [
      "%(cnt)d t\u1ed5ng s\u1ed1 b\u00e0i \u0111\u00e3 g\u1eedi"
    ],
    "%(sel)s of %(cnt)s selected": [
      " %(sel)s  c\u1ee7a %(cnt)s \u0111\u01b0\u1ee3c ch\u1ecdn"
    ],
    "6 a.m.": "6 gi\u1edd s\u00e1ng",
    "6 p.m.": "6 gi\u1edd chi\u1ec1u",
    "April": "Th\u00e1ng T\u01b0",
    "August": "Th\u00e1ng T\u00e1m",
    "Available %s": "C\u00f3 s\u1eb5n %s",
    "Cancel": "H\u1ee7y b\u1ecf",
    "Choose": "Ch\u1ecdn",
    "Choose a Date": "Ch\u1ecdn Ng\u00e0y",
    "Choose a Time": "Ch\u1ecdn Th\u1eddi gian",
    "Choose a time": "Ch\u1ecdn gi\u1edd",
    "Choose all": "Ch\u1ecdn t\u1ea5t c\u1ea3",
    "Chosen %s": "Ch\u1ecdn %s",
    "Click to choose all %s at once.": "Click \u0111\u1ec3 ch\u1ecdn t\u1ea5t c\u1ea3 %s .",
    "Click to remove all chosen %s at once.": "Click \u0111\u1ec3 b\u1ecf ch\u1ecdn t\u1ea5t c\u1ea3 %s",
    "December": "Th\u00e1ng M\u01b0\u1eddi Hai",
    "Edit points vote (%s)": "S\u1eeda \u0111i\u1ec3m vote (%s)",
    "February": "Th\u00e1ng Hai",
    "Filter": "L\u1ecdc",
    "Hide": "D\u1ea5u \u0111i",
    "January": "Th\u00e1ng M\u1ed9t",
    "July": "Th\u00e1ng B\u1ea3y",
    "June": "Th\u00e1ng S\u00e1u",
    "March": "Th\u00e1ng Ba",
    "May": "Th\u00e1ng N\u0103m",
    "Midnight": "N\u1eeda \u0111\u00eam",
    "Noon": "Bu\u1ed5i tr\u01b0a",
    "Note: You are %s hour ahead of server time.": [
      "L\u01b0u \u00fd: Hi\u1ec7n t\u1ea1i b\u1ea1n \u0111ang th\u1ea5y th\u1eddi gian tr\u01b0\u1edbc %s gi\u1edd so v\u1edbi th\u1eddi gian m\u00e1y ch\u1ee7."
    ],
    "Note: You are %s hour behind server time.": [
      "L\u01b0u \u00fd: Hi\u1ec7n t\u1ea1i b\u1ea1n \u0111ang th\u1ea5y th\u1eddi gian sau %s gi\u1edd so v\u1edbi th\u1eddi gian m\u00e1y ch\u1ee7."
    ],
    "November": "Th\u00e1ng M\u01b0\u1eddi M\u1ed9t",
    "Now": "B\u00e2y gi\u1edd",
    "Number of votes for this point value": "S\u1ed1 l\u01b0\u1ee3ng b\u00ecnh ch\u1ecdn cho \u0111i\u1ec3m n\u00e0y",
    "October": "Th\u00e1ng M\u01b0\u1eddi",
    "Remove": "X\u00f3a",
    "Remove all": "Xo\u00e1 t\u1ea5t c\u1ea3",
    "September": "Th\u00e1ng Ch\u00edn",
    "Show": "Hi\u1ec7n ra",
    "This is the list of available %s. You may choose some by selecting them in the box below and then clicking the \"Choose\" arrow between the two boxes.": "Danh s\u00e1ch c\u00e1c l\u1ef1a ch\u1ecdn \u0111ang c\u00f3 %s. B\u1ea1n c\u00f3 th\u1ec3 ch\u1ecdn b\u1eb1ng b\u00e1ch click v\u00e0o m\u0169i t\u00ean \"Ch\u1ecdn\" n\u1eb1m gi\u1eefa hai h\u1ed9p.",
    "This is the list of chosen %s. You may remove some by selecting them in the box below and then clicking the \"Remove\" arrow between the two boxes.": "Danh s\u00e1ch b\u1ea1n \u0111\u00e3 ch\u1ecdn %s. B\u1ea1n c\u00f3 th\u1ec3 b\u1ecf ch\u1ecdn b\u1eb1ng c\u00e1ch click v\u00e0o m\u0169i t\u00ean \"Xo\u00e1\" n\u1eb1m gi\u1eefa hai \u00f4.",
    "Today": "H\u00f4m nay",
    "Tomorrow": "Ng\u00e0y mai",
    "Type into this box to filter down the list of available %s.": "B\u1ea1n h\u00e3y nh\u1eadp v\u00e0o \u00f4 n\u00e0y \u0111\u1ec3 l\u1ecdc c\u00e1c danh s\u00e1ch sau %s.",
    "Unable to cast vote: %s": "Kh\u00f4ng th\u1ec3 s\u1eeda \u0111i\u1ec3m: %s",
    "Unable to delete vote: %s": "Kh\u00f4ng th\u1ec3 s\u1eeda \u0111i\u1ec3m: %s",
    "Vote on problem points": "B\u00ecnh ch\u1ecdn \u0111i\u1ec3m c\u1ee7a b\u00e0i t\u1eadp",
    "Yesterday": "H\u00f4m qua",
    "You have selected an action, and you haven\u2019t made any changes on individual fields. You\u2019re probably looking for the Go button rather than the Save button.": "B\u1ea1n \u0111\u00e3 ch\u1ecdn m\u1ed9t h\u00e0nh \u0111\u1ed9ng v\u00e0 b\u1ea1n \u0111\u00e3 kh\u00f4ng th\u1ef1c hi\u1ec7n b\u1ea5t k\u1ef3 thay \u0111\u1ed5i n\u00e0o tr\u00ean c\u00e1c tr\u01b0\u1eddng. C\u00f3 l\u1ebd b\u1ea1n n\u00ean b\u1ea5m n\u00fat \u0110i \u0111\u1ebfn h\u01a1n l\u00e0 n\u00fat L\u01b0u l\u1ea1i.",
    "You have selected an action, but you haven\u2019t saved your changes to individual fields yet. Please click OK to save. You\u2019ll need to re-run the action.": "B\u1ea1n \u0111\u00e3 ch\u1ecdn m\u1ed9t h\u00e0nh \u0111\u1ed9ng, nh\u01b0ng b\u1ea1n ch\u01b0a l\u01b0u c\u00e1c thay \u0111\u1ed5i tr\u00ean c\u00e1c tr\u01b0\u1eddng. Vui l\u00f2ng b\u1ea5m OK \u0111\u1ec3 l\u01b0u l\u1ea1i. B\u1ea1n s\u1ebd c\u1ea7n ch\u1ea1y l\u1ea1i h\u00e0nh d\u1ed9ng.",
    "You have unsaved changes on individual editable fields. If you run an action, your unsaved changes will be lost.": "B\u1ea1n ch\u01b0a l\u01b0u nh\u1eefng tr\u01b0\u1eddng \u0111\u00e3 ch\u1ec9nh s\u1eeda. N\u1ebfu b\u1ea1n ch\u1ecdn h\u00e0nh \u0111\u1ed9ng n\u00e0y, nh\u1eefng ch\u1ec9nh s\u1eeda ch\u01b0a \u0111\u01b0\u1ee3c l\u01b0u s\u1ebd b\u1ecb m\u1ea5t.",
    "abbrev. month April\u0004Apr": "Th\u00e1ng T\u01b0",
    "abbrev. month August\u0004Aug": "Th\u00e1ng T\u00e1m",
    "abbrev. month December\u0004Dec": "Th\u00e1ng M\u01b0\u1eddi Hai",
    "abbrev. month February\u0004Feb": "Th\u00e1ng Hai",
    "abbrev. month January\u0004Jan": "Th\u00e1ng M\u1ed9t",
    "abbrev. month July\u0004Jul": "Th\u00e1ng B\u1ea3y",
    "abbrev. month June\u0004Jun": "Th\u00e1ng S\u00e1u",
    "abbrev. month March\u0004Mar": "Th\u00e1ng Ba",
    "abbrev. month May\u0004May": "Th\u00e1ng N\u0103m",
    "abbrev. month November\u0004Nov": "Th\u00e1ng M\u01b0\u1eddi M\u1ed9t",
    "abbrev. month October\u0004Oct": "Th\u00e1ng M\u01b0\u1eddi",
    "abbrev. month September\u0004Sep": "Th\u00e1ng Ch\u00edn",
    "one letter Friday\u0004F": "6",
    "one letter Monday\u0004M": "2",
    "one letter Saturday\u0004S": "7",
    "one letter Sunday\u0004S": "CN",
    "one letter Thursday\u0004T": "5",
    "one letter Tuesday\u0004T": "3",
    "one letter Wednesday\u0004W": "4",
    "past year": "m\u1ed9t n\u0103m tr\u01b0\u1edbc",
    "time format with day\u0004%d day %h:%m:%s": [
      "%d ng\u00e0y %h:%m:%s"
    ],
    "time format without day\u0004%h:%m:%s": "%h:%m:%s"
  };
  for (const key in newcatalog) {
    django.catalog[key] = newcatalog[key];
  }
  

  if (!django.jsi18n_initialized) {
    django.gettext = function(msgid) {
      const value = django.catalog[msgid];
      if (typeof value === 'undefined') {
        return msgid;
      } else {
        return (typeof value === 'string') ? value : value[0];
      }
    };

    django.ngettext = function(singular, plural, count) {
      const value = django.catalog[singular];
      if (typeof value === 'undefined') {
        return (count == 1) ? singular : plural;
      } else {
        return value.constructor === Array ? value[django.pluralidx(count)] : value;
      }
    };

    django.gettext_noop = function(msgid) { return msgid; };

    django.pgettext = function(context, msgid) {
      let value = django.gettext(context + '\x04' + msgid);
      if (value.includes('\x04')) {
        value = msgid;
      }
      return value;
    };

    django.npgettext = function(context, singular, plural, count) {
      let value = django.ngettext(context + '\x04' + singular, context + '\x04' + plural, count);
      if (value.includes('\x04')) {
        value = django.ngettext(singular, plural, count);
      }
      return value;
    };

    django.interpolate = function(fmt, obj, named) {
      if (named) {
        return fmt.replace(/%\(\w+\)s/g, function(match){return String(obj[match.slice(2,-2)])});
      } else {
        return fmt.replace(/%s/g, function(match){return String(obj.shift())});
      }
    };


    /* formatting library */

    django.formats = {
    "DATETIME_FORMAT": "H:i \\N\\g\u00e0\\y d \\t\\h\u00e1\\n\\g n \\n\u0103\\m Y",
    "DATETIME_INPUT_FORMATS": [
      "%Y-%m-%d %H:%M:%S",
      "%Y-%m-%d %H:%M:%S.%f",
      "%Y-%m-%d %H:%M",
      "%m/%d/%Y %H:%M:%S",
      "%m/%d/%Y %H:%M:%S.%f",
      "%m/%d/%Y %H:%M",
      "%m/%d/%y %H:%M:%S",
      "%m/%d/%y %H:%M:%S.%f",
      "%m/%d/%y %H:%M"
    ],
    "DATE_FORMAT": "\\N\\g\u00e0\\y d \\t\\h\u00e1\\n\\g n \\n\u0103\\m Y",
    "DATE_INPUT_FORMATS": [
      "%Y-%m-%d",
      "%m/%d/%Y",
      "%m/%d/%y",
      "%b %d %Y",
      "%b %d, %Y",
      "%d %b %Y",
      "%d %b, %Y",
      "%B %d %Y",
      "%B %d, %Y",
      "%d %B %Y",
      "%d %B, %Y"
    ],
    "DECIMAL_SEPARATOR": ",",
    "FIRST_DAY_OF_WEEK": 0,
    "MONTH_DAY_FORMAT": "j F",
    "NUMBER_GROUPING": 0,
    "SHORT_DATETIME_FORMAT": "H:i d-m-Y",
    "SHORT_DATE_FORMAT": "d-m-Y",
    "THOUSAND_SEPARATOR": ".",
    "TIME_FORMAT": "H:i",
    "TIME_INPUT_FORMATS": [
      "%H:%M:%S",
      "%H:%M:%S.%f",
      "%H:%M"
    ],
    "YEAR_MONTH_FORMAT": "F Y"
  };

    django.get_format = function(format_type) {
      const value = django.formats[format_type];
      if (typeof value === 'undefined') {
        return format_type;
      } else {
        return value;
      }
    };

    /* add to global namespace */
    globals.pluralidx = django.pluralidx;
    globals.gettext = django.gettext;
    globals.ngettext = django.ngettext;
    globals.gettext_noop = django.gettext_noop;
    globals.pgettext = django.pgettext;
    globals.npgettext = django.npgettext;
    globals.interpolate = django.interpolate;
    globals.get_format = django.get_format;

    django.jsi18n_initialized = true;
  }
};

