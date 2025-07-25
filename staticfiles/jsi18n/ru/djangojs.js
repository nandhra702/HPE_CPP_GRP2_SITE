

'use strict';
{
  const globals = this;
  const django = globals.django || (globals.django = {});

  
  django.pluralidx = function(n) {
    const v = ((n%10==1 && n%100!=11) ? 0 : ((n%10 >= 2 && n%10 <=4 && (n%100 < 12 || n%100 > 14)) ? 1 : ((n%10 == 0 || (n%10 >= 5 && n%10 <=9)) || (n%100 >= 11 && n%100 <= 14)) ? 2 : 3));
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
      "%(cnt)d \u043f\u043e\u0441\u044b\u043b\u043a\u0430 \u0432 %(year)d",
      "%(cnt)d \u043f\u043e\u0441\u044b\u043b\u043a\u0438 \u0432 %(year)d",
      "%(cnt)d \u043f\u043e\u0441\u044b\u043b\u043e\u043a \u0432 %(year)d",
      "%(cnt)d \u043f\u043e\u0441\u044b\u043b\u043e\u043a \u0432 %(year)d"
    ],
    "%(cnt)d submission in the last year": [
      "%(cnt)d \u043f\u043e\u0441\u044b\u043b\u043a\u0430 \u0437\u0430 \u043f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0439 \u0433\u043e\u0434",
      "%(cnt)d \u043f\u043e\u0441\u044b\u043b\u043a\u0438 \u0437\u0430 \u043f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0439 \u0433\u043e\u0434",
      "%(cnt)d \u043f\u043e\u0441\u044b\u043b\u043e\u043a \u0437\u0430 \u043f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0439 \u0433\u043e\u0434",
      "%(cnt)d \u043f\u043e\u0441\u044b\u043b\u043e\u043a \u0437\u0430 \u043f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0439 \u0433\u043e\u0434"
    ],
    "%(cnt)d submission on %(date)s": [
      "%(cnt)d \u043f\u043e\u0441\u044b\u043b\u043a\u0430 %(date)s",
      "%(cnt)d \u043f\u043e\u0441\u044b\u043b\u043a\u0438 %(date)s",
      "%(cnt)d \u043f\u043e\u0441\u044b\u043b\u043e\u043a %(date)s",
      "%(cnt)d \u043f\u043e\u0441\u044b\u043b\u043e\u043a %(date)s"
    ],
    "%(cnt)d total submission": [
      "\u0412\u0441\u0435\u0433\u043e %(cnt)d \u043f\u043e\u0441\u044b\u043b\u043a\u0430",
      "\u0412\u0441\u0435\u0433\u043e %(cnt)d \u043f\u043e\u0441\u044b\u043b\u043a\u0438",
      "\u0412\u0441\u0435\u0433\u043e %(cnt)d \u043f\u043e\u0441\u044b\u043b\u043e\u043a",
      "\u0412\u0441\u0435\u0433\u043e %(cnt)d \u043f\u043e\u0441\u044b\u043b\u043e\u043a"
    ],
    "%(sel)s of %(cnt)s selected": [
      "\u0412\u044b\u0431\u0440\u0430\u043d %(sel)s \u0438\u0437 %(cnt)s",
      "\u0412\u044b\u0431\u0440\u0430\u043d\u043e %(sel)s \u0438\u0437 %(cnt)s",
      "\u0412\u044b\u0431\u0440\u0430\u043d\u043e %(sel)s \u0438\u0437 %(cnt)s",
      "\u0412\u044b\u0431\u0440\u0430\u043d\u043e %(sel)s \u0438\u0437 %(cnt)s"
    ],
    "6 a.m.": "6 \u0443\u0442\u0440\u0430",
    "6 p.m.": "6 \u0432\u0435\u0447\u0435\u0440\u0430",
    "April": "\u0410\u043f\u0440\u0435\u043b\u044c",
    "August": "\u0410\u0432\u0433\u0443\u0441\u0442",
    "Available %s": "\u0414\u043e\u0441\u0442\u0443\u043f\u043d\u044b\u0435 %s",
    "Cancel": "\u041e\u0442\u043c\u0435\u043d\u0430",
    "Choose": "\u0412\u044b\u0431\u0440\u0430\u0442\u044c",
    "Choose a Date": "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0434\u0430\u0442\u0443",
    "Choose a Time": "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0432\u0440\u0435\u043c\u044f",
    "Choose a time": "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0432\u0440\u0435\u043c\u044f",
    "Choose all": "\u0412\u044b\u0431\u0440\u0430\u0442\u044c \u0432\u0441\u0435",
    "Chosen %s": "\u0412\u044b\u0431\u0440\u0430\u043d\u043d\u044b\u0435 %s",
    "Click to choose all %s at once.": "\u041d\u0430\u0436\u043c\u0438\u0442\u0435, \u0447\u0442\u043e\u0431\u044b \u0432\u044b\u0431\u0440\u0430\u0442\u044c \u0432\u0441\u0435 %s \u0441\u0440\u0430\u0437\u0443.",
    "Click to remove all chosen %s at once.": "\u041d\u0430\u0436\u043c\u0438\u0442\u0435 \u0447\u0442\u043e\u0431\u044b \u0443\u0434\u0430\u043b\u0438\u0442\u044c \u0432\u0441\u0435 %s \u0441\u0440\u0430\u0437\u0443.",
    "December": "\u0414\u0435\u043a\u0430\u0431\u0440\u044c",
    "Edit points vote (%s)": "\u0418\u0437\u043c\u0435\u043d\u0438\u0442\u044c \u043e\u0446\u0435\u043d\u043a\u0443 \u0437\u0430\u0434\u0430\u0447\u0438 (%s)",
    "February": "\u0424\u0435\u0432\u0440\u0430\u043b\u044c",
    "Filter": "\u0424\u0438\u043b\u044c\u0442\u0440",
    "Hide": "\u0421\u043a\u0440\u044b\u0442\u044c",
    "January": "\u042f\u043d\u0432\u0430\u0440\u044c",
    "July": "\u0418\u044e\u043b\u044c",
    "June": "\u0418\u044e\u043d\u044c",
    "March": "\u041c\u0430\u0440\u0442",
    "May": "\u041c\u0430\u0439",
    "Midnight": "\u041f\u043e\u043b\u043d\u043e\u0447\u044c",
    "Noon": "\u041f\u043e\u043b\u0434\u0435\u043d\u044c",
    "Note: You are %s hour ahead of server time.": [
      "\u0412\u043d\u0438\u043c\u0430\u043d\u0438\u0435: \u0412\u0430\u0448\u0435 \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0435 \u0432\u0440\u0435\u043c\u044f \u043e\u043f\u0435\u0440\u0435\u0436\u0430\u0435\u0442 \u0432\u0440\u0435\u043c\u044f \u0441\u0435\u0440\u0432\u0435\u0440\u0430 \u043d\u0430 %s \u0447\u0430\u0441.",
      "\u0412\u043d\u0438\u043c\u0430\u043d\u0438\u0435: \u0412\u0430\u0448\u0435 \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0435 \u0432\u0440\u0435\u043c\u044f \u043e\u043f\u0435\u0440\u0435\u0436\u0430\u0435\u0442 \u0432\u0440\u0435\u043c\u044f \u0441\u0435\u0440\u0432\u0435\u0440\u0430 \u043d\u0430 %s \u0447\u0430\u0441\u0430.",
      "\u0412\u043d\u0438\u043c\u0430\u043d\u0438\u0435: \u0412\u0430\u0448\u0435 \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0435 \u0432\u0440\u0435\u043c\u044f \u043e\u043f\u0435\u0440\u0435\u0436\u0430\u0435\u0442 \u0432\u0440\u0435\u043c\u044f \u0441\u0435\u0440\u0432\u0435\u0440\u0430 \u043d\u0430 %s \u0447\u0430\u0441\u043e\u0432.",
      "\u0412\u043d\u0438\u043c\u0430\u043d\u0438\u0435: \u0412\u0430\u0448\u0435 \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0435 \u0432\u0440\u0435\u043c\u044f \u043e\u043f\u0435\u0440\u0435\u0436\u0430\u0435\u0442 \u0432\u0440\u0435\u043c\u044f \u0441\u0435\u0440\u0432\u0435\u0440\u0430 \u043d\u0430 %s \u0447\u0430\u0441\u043e\u0432."
    ],
    "Note: You are %s hour behind server time.": [
      "\u0412\u043d\u0438\u043c\u0430\u043d\u0438\u0435: \u0412\u0430\u0448\u0435 \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0435 \u0432\u0440\u0435\u043c\u044f \u043e\u0442\u0441\u0442\u0430\u0451\u0442 \u043e\u0442 \u0432\u0440\u0435\u043c\u0435\u043d\u0438 \u0441\u0435\u0440\u0432\u0435\u0440\u0430 \u043d\u0430 %s \u0447\u0430\u0441.",
      "\u0412\u043d\u0438\u043c\u0430\u043d\u0438\u0435: \u0412\u0430\u0448\u0435 \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0435 \u0432\u0440\u0435\u043c\u044f \u043e\u0442\u0441\u0442\u0430\u0451\u0442 \u043e\u0442 \u0432\u0440\u0435\u043c\u0435\u043d\u0438 \u0441\u0435\u0440\u0432\u0435\u0440\u0430 \u043d\u0430 %s \u0447\u0430\u0441\u0430.",
      "\u0412\u043d\u0438\u043c\u0430\u043d\u0438\u0435: \u0412\u0430\u0448\u0435 \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0435 \u0432\u0440\u0435\u043c\u044f \u043e\u0442\u0441\u0442\u0430\u0451\u0442 \u043e\u0442 \u0432\u0440\u0435\u043c\u0435\u043d\u0438 \u0441\u0435\u0440\u0432\u0435\u0440\u0430 \u043d\u0430 %s \u0447\u0430\u0441\u043e\u0432.",
      "\u0412\u043d\u0438\u043c\u0430\u043d\u0438\u0435: \u0412\u0430\u0448\u0435 \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0435 \u0432\u0440\u0435\u043c\u044f \u043e\u0442\u0441\u0442\u0430\u0451\u0442 \u043e\u0442 \u0432\u0440\u0435\u043c\u0435\u043d\u0438 \u0441\u0435\u0440\u0432\u0435\u0440\u0430 \u043d\u0430 %s \u0447\u0430\u0441\u043e\u0432."
    ],
    "November": "\u041d\u043e\u044f\u0431\u0440\u044c",
    "Now": "\u0421\u0435\u0439\u0447\u0430\u0441",
    "Number of votes for this point value": "\u041a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e \u0433\u043e\u043b\u043e\u0441\u043e\u0432 \u0437\u0430 \u0443\u043a\u0430\u0437\u0430\u043d\u043d\u043e\u0435 \u043a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e \u0431\u0430\u043b\u043b\u043e\u0432",
    "October": "\u041e\u043a\u0442\u044f\u0431\u0440\u044c",
    "Remove": "\u0423\u0434\u0430\u043b\u0438\u0442\u044c",
    "Remove all": "\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u0432\u0441\u0435",
    "September": "\u0421\u0435\u043d\u0442\u044f\u0431\u0440\u044c",
    "Show": "\u041f\u043e\u043a\u0430\u0437\u0430\u0442\u044c",
    "This is the list of available %s. You may choose some by selecting them in the box below and then clicking the \"Choose\" arrow between the two boxes.": "\u042d\u0442\u043e \u0441\u043f\u0438\u0441\u043e\u043a \u0432\u0441\u0435\u0445 \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b\u0445 %s. \u0412\u044b \u043c\u043e\u0436\u0435\u0442\u0435 \u0432\u044b\u0431\u0440\u0430\u0442\u044c \u043d\u0435\u043a\u043e\u0442\u043e\u0440\u044b\u0435 \u0438\u0437 \u043d\u0438\u0445, \u0432\u044b\u0434\u0435\u043b\u0438\u0432 \u0438\u0445 \u0432 \u043f\u043e\u043b\u0435 \u043d\u0438\u0436\u0435 \u0438 \u043a\u043b\u0438\u043a\u043d\u0443\u0432 \"\u0412\u044b\u0431\u0440\u0430\u0442\u044c\", \u043b\u0438\u0431\u043e \u0434\u0432\u043e\u0439\u043d\u044b\u043c \u0449\u0435\u043b\u0447\u043a\u043e\u043c.",
    "This is the list of chosen %s. You may remove some by selecting them in the box below and then clicking the \"Remove\" arrow between the two boxes.": "\u042d\u0442\u043e \u0441\u043f\u0438\u0441\u043e\u043a \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u044b\u0445 %s. \u0412\u044b \u043c\u043e\u0436\u0435\u0442\u0435 \u0443\u0434\u0430\u043b\u0438\u0442\u044c \u043d\u0435\u043a\u043e\u0442\u043e\u0440\u044b\u0435 \u0438\u0437 \u043d\u0438\u0445, \u0432\u044b\u0434\u0435\u043b\u0438\u0432 \u0438\u0445 \u0432 \u043f\u043e\u043b\u0435 \u043d\u0438\u0436\u0435 \u0438 \u043a\u043b\u0438\u043a\u043d\u0443\u0432 \"\u0423\u0434\u0430\u043b\u0438\u0442\u044c\", \u043b\u0438\u0431\u043e \u0434\u0432\u043e\u0439\u043d\u044b\u043c \u0449\u0435\u043b\u0447\u043a\u043e\u043c.",
    "Today": "\u0421\u0435\u0433\u043e\u0434\u043d\u044f",
    "Tomorrow": "\u0417\u0430\u0432\u0442\u0440\u0430",
    "Type into this box to filter down the list of available %s.": "\u041d\u0430\u0447\u043d\u0438\u0442\u0435 \u0432\u0432\u043e\u0434\u0438\u0442\u044c \u0442\u0435\u043a\u0441\u0442 \u0432 \u044d\u0442\u043e\u043c \u043f\u043e\u043b\u0435, \u0447\u0442\u043e\u0431\u044b \u043e\u0442\u0444\u0438\u0442\u0440\u043e\u0432\u0430\u0442\u044c \u0441\u043f\u0438\u0441\u043e\u043a \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b\u0445 %s.",
    "Unable to cast vote: %s": "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043f\u0440\u043e\u0433\u043e\u043b\u043e\u0441\u043e\u0432\u0430\u0442\u044c: %s",
    "Unable to delete vote: %s": "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0443\u0434\u0430\u043b\u0438\u0442\u044c \u0433\u043e\u043b\u043e\u0441: %s",
    "Vote on problem points": "\u0413\u043e\u043b\u043e\u0441\u043e\u0432\u0430\u0442\u044c \u0437\u0430 \u043e\u0446\u0435\u043d\u043a\u0443 \u0437\u0430\u0434\u0430\u0447\u0438",
    "Yesterday": "\u0412\u0447\u0435\u0440\u0430",
    "You have already submitted this form. Are you sure you want to submit it again?": "\u0412\u044b \u0443\u0436\u0435 \u043e\u0442\u043f\u0440\u0430\u0432\u0438\u043b\u0438 \u044d\u0442\u0443 \u0444\u043e\u0440\u043c\u0443. \u0412\u044b \u0443\u0432\u0435\u0440\u0435\u043d\u044b, \u0447\u0442\u043e \u0445\u043e\u0442\u0438\u0442\u0435 \u043e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u0435\u0451 \u0435\u0449\u0451 \u0440\u0430\u0437?",
    "You have selected an action, and you haven\u2019t made any changes on individual fields. You\u2019re probably looking for the Go button rather than the Save button.": "\u0412\u044b \u0432\u044b\u0431\u0440\u0430\u043b\u0438 \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0435 \u0438 \u043d\u0435 \u0432\u043d\u0435\u0441\u043b\u0438 \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u0439 \u0432 \u0434\u0430\u043d\u043d\u044b\u0435. \u0412\u043e\u0437\u043c\u043e\u0436\u043d\u043e, \u0432\u044b \u0445\u043e\u0442\u0435\u043b\u0438 \u0432\u043e\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u044c\u0441\u044f \u043a\u043d\u043e\u043f\u043a\u043e\u0439 \"\u0412\u044b\u043f\u043e\u043b\u043d\u0438\u0442\u044c\", \u0430 \u043d\u0435 \u043a\u043d\u043e\u043f\u043a\u043e\u0439 \"\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c\". \u0415\u0441\u043b\u0438 \u044d\u0442\u043e \u0442\u0430\u043a, \u0442\u043e \u043d\u0430\u0436\u043c\u0438\u0442\u0435 \"\u041e\u0442\u043c\u0435\u043d\u0430\", \u0447\u0442\u043e\u0431\u044b \u0432\u0435\u0440\u043d\u0443\u0442\u044c\u0441\u044f \u0432 \u0438\u043d\u0442\u0435\u0440\u0444\u0435\u0439\u0441 \u0440\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u044f.",
    "You have selected an action, but you haven\u2019t saved your changes to individual fields yet. Please click OK to save. You\u2019ll need to re-run the action.": "\u0412\u044b \u0432\u044b\u0431\u0440\u0430\u043b\u0438 \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0435, \u043d\u043e \u0435\u0449\u0435 \u043d\u0435 \u0441\u043e\u0445\u0440\u0430\u043d\u0438\u043b\u0438 \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u044f, \u0432\u043d\u0435\u0441\u0435\u043d\u043d\u044b\u0435 \u0432 \u043d\u0435\u043a\u043e\u0442\u043e\u0440\u044b\u0445 \u043f\u043e\u043b\u044f\u0445 \u0434\u043b\u044f \u0440\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u044f. \u041d\u0430\u0436\u043c\u0438\u0442\u0435 OK, \u0447\u0442\u043e\u0431\u044b \u0441\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u044f. \u041f\u043e\u0441\u043b\u0435 \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0438\u044f \u0432\u0430\u043c \u043f\u0440\u0438\u0434\u0435\u0442\u0441\u044f \u0437\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u044c \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0435 \u0435\u0449\u0435 \u0440\u0430\u0437.",
    "You have unsaved changes on individual editable fields. If you run an action, your unsaved changes will be lost.": "\u0418\u043c\u0435\u044e\u0442\u0441\u044f \u043d\u0435\u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u043d\u044b\u0435 \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u044f \u0432 \u043e\u0442\u0434\u0435\u043b\u044c\u043d\u044b\u0445 \u043f\u043e\u043b\u044f\u0445 \u0434\u043b\u044f \u0440\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u044f. \u0415\u0441\u043b\u0438 \u0432\u044b \u0437\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u0435 \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0435, \u043d\u0435\u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u043d\u044b\u0435 \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u044f \u0431\u0443\u0434\u0443\u0442 \u043f\u043e\u0442\u0435\u0440\u044f\u043d\u044b.",
    "abbrev. month April\u0004Apr": "\u0410\u043f\u0440",
    "abbrev. month August\u0004Aug": "\u0410\u0432\u0433",
    "abbrev. month December\u0004Dec": "\u0414\u0435\u043a",
    "abbrev. month February\u0004Feb": "\u0424\u0435\u0432",
    "abbrev. month January\u0004Jan": "\u042f\u043d\u0432",
    "abbrev. month July\u0004Jul": "\u0418\u044e\u043b",
    "abbrev. month June\u0004Jun": "\u0418\u044e\u043d",
    "abbrev. month March\u0004Mar": "\u041c\u0430\u0440",
    "abbrev. month May\u0004May": "\u041c\u0430\u0439",
    "abbrev. month November\u0004Nov": "\u041d\u043e\u044f",
    "abbrev. month October\u0004Oct": "\u041e\u043a\u0442",
    "abbrev. month September\u0004Sep": "\u0421\u0435\u043d",
    "one letter Friday\u0004F": "\u041f",
    "one letter Monday\u0004M": "\u041f",
    "one letter Saturday\u0004S": "\u0421",
    "one letter Sunday\u0004S": "\u0412",
    "one letter Thursday\u0004T": "\u0427",
    "one letter Tuesday\u0004T": "\u0412",
    "one letter Wednesday\u0004W": "\u0421",
    "past year": "\u043f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0439 \u0433\u043e\u0434",
    "time format with day\u0004%d day %h:%m:%s": [
      "%d \u0434\u0435\u043d\u044c %h:%m:%s",
      "%d \u0434\u043d\u044f %h:%m:%s",
      "%d \u0434\u043d\u0435\u0439 %h:%m:%s",
      "%d \u0434\u043d\u044f %h:%m:%s"
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
    "DATETIME_FORMAT": "j E Y \u0433. G:i",
    "DATETIME_INPUT_FORMATS": [
      "%d.%m.%Y %H:%M:%S",
      "%d.%m.%Y %H:%M:%S.%f",
      "%d.%m.%Y %H:%M",
      "%d.%m.%y %H:%M:%S",
      "%d.%m.%y %H:%M:%S.%f",
      "%d.%m.%y %H:%M",
      "%Y-%m-%d %H:%M:%S",
      "%Y-%m-%d %H:%M:%S.%f",
      "%Y-%m-%d %H:%M",
      "%Y-%m-%d"
    ],
    "DATE_FORMAT": "j E Y \u0433.",
    "DATE_INPUT_FORMATS": [
      "%d.%m.%Y",
      "%d.%m.%y",
      "%Y-%m-%d"
    ],
    "DECIMAL_SEPARATOR": ",",
    "FIRST_DAY_OF_WEEK": 1,
    "MONTH_DAY_FORMAT": "j F",
    "NUMBER_GROUPING": 3,
    "SHORT_DATETIME_FORMAT": "d.m.Y H:i",
    "SHORT_DATE_FORMAT": "d.m.Y",
    "THOUSAND_SEPARATOR": "\u00a0",
    "TIME_FORMAT": "G:i",
    "TIME_INPUT_FORMATS": [
      "%H:%M:%S",
      "%H:%M:%S.%f",
      "%H:%M"
    ],
    "YEAR_MONTH_FORMAT": "F Y \u0433."
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

