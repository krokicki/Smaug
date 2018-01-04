alter table ircview_quotelink engine=MYISAM;
create fulltext index quotelink_ftidx on ircview_quotelink (match_text);
