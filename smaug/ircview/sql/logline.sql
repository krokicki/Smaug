alter table ircview_logline modify column body longtext character set utf8 collate utf8_general_ci not null;
alter table ircview_logline modify column handle varchar(64) character set utf8 collate utf8_general_ci null;
create fulltext index logline_ftidx on ircview_logline (body);
create index logline_year_month on ircview_logline (year,month);

