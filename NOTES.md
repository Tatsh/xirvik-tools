# Random notes

- VM hard power off - `https://HOST/userpanel/index.php/virtual_machine/poweroff`
- VM start - `https://HOST/userpanel/index.php/services/start/plex_vm`

## `setsettings` (tabs in UI, etc)

Some settings are plugin-specific!

```javascript
const d = new FormData({
  v: JSON.stringify({
    'webui.alternate_color': 1,
    'webui.closed_panels': {
      flabel: 1,
      mailbox: 0,
      plabel: 0,
      prss: 1,
      pstate: 0,
      ptrackers: 0,
    },
    'webui.confirm_when_deleting': 1,
    'webui.dateformat': '1',
    'webui.dmcaFiles.colenabled': [1, 1, 1, 1],
    'webui.dmcaFiles.colorder': [0, 1, 2, 3],
    'webui.dmcaFiles.colwidth': [384, 100, 100, 100],
    'webui.dmcaFiles.rev': 0,
    'webui.dmcaFiles.rev2': 0,
    'webui.dmcaFiles.sindex': 0,
    'webui.dmcaFiles.sindex2': 0,
    'webui.dmcaTrackers.colenabled': [1, 1, 1, 1],
    'webui.dmcaTrackers.colorder': [0, 1, 2, 3],
    'webui.dmcaTrackers.colwidth': [250, 100, 100, 100],
    'webui.dmcaTrackers.rev': 0,
    'webui.dmcaTrackers.rev2': 0,
    'webui.dmcaTrackers.sindex': 0,
    'webui.dmcaTrackers.sindex2': 0,
    'webui.effects': 0,
    'webui.exp_l.colenabled': [1, 1, 1],
    'webui.exp_l.colorder': [0, 1, 2],
    'webui.exp_l.colwidth': [200, 100, 110],
    'webui.exp_l.rev': 0,
    'webui.exp_l.rev2': 0,
    'webui.exp_l.sindex': -1,
    'webui.exp_l.sindex2': 0,
    'webui.exp_r.colenabled': [1, 1, 1],
    'webui.exp_r.colorder': [0, 1, 2],
    'webui.exp_r.colwidth': [200, 100, 110],
    'webui.exp_r.rev': 0,
    'webui.exp_r.rev2': 0,
    'webui.exp_r.sindex': -1,
    'webui.exp_r.sindex2': 0,
    'webui.ext.colenabled': [1, 1, 1],
    'webui.ext.colorder': [0, 1, 2],
    'webui.ext.colwidth': [400, 100, 100],
    'webui.ext.rev': 0,
    'webui.ext.rev2': 0,
    'webui.ext.sindex': -1,
    'webui.ext.sindex2': 0,
    'webui.fls.colenabled': [1, 1, 1, 1, 1],
    'webui.fls.colorder': [0, 1, 2, 3, 4],
    'webui.fls.colwidth': [200, 60, 100, 100, 80],
    'webui.fls.rev': 1,
    'webui.fls.rev2': 0,
    'webui.fls.sindex': 3,
    'webui.fls.sindex2': 0,
    'webui.fls.view': 0,
    'webui.fullrows': 0,
    'webui.hsplit': 0.842,
    'webui.hst.colenabled': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    'webui.hst.colorder': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    'webui.hst.colwidth': [200, 100, 100, 60, 100, 100, 60, 60, 100, 100, 100, 100],
    'webui.hst.rev': 0,
    'webui.hst.rev2': 0,
    'webui.hst.sindex': -1,
    'webui.hst.sindex2': 0,
    'webui.ignore_timeouts': 0,
    'webui.lang': 'en',
    'webui.log_autoswitch': 1,
    'webui.mail.colenabled': [1, 1, 1, 1],
    'webui.mail.colorder': [0, 1, 2, 3],
    'webui.mail.colwidth': [400, 200, 100, 110],
    'webui.mail.rev': 0,
    'webui.mail.rev2': 0,
    'webui.mail.sindex': -1,
    'webui.mail.sindex2': 0,
    'webui.needmessage': 1,
    'webui.no_delaying_draw': 1,
    'webui.plg.colenabled': [1, 1, 1, 1, 1, 1],
    'webui.plg.colorder': [0, 1, 2, 3, 4, 5],
    'webui.plg.colwidth': [150, 60, 80, 80, 80, 500],
    'webui.plg.rev': 0,
    'webui.plg.rev2': 0,
    'webui.plg.sindex': 2,
    'webui.plg.sindex2': 0,
    'webui.prs.colenabled': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    'webui.prs.colorder': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    'webui.prs.colwidth': [60, 100, 120, 60, 100, 100, 100, 60, 60, 60, 100, 200],
    'webui.prs.rev': 0,
    'webui.prs.rev2': 0,
    'webui.prs.sindex': -1,
    'webui.prs.sindex2': 0,
    'webui.register_magnet': 0,
    'webui.reqtimeout': '60000',
    'webui.retry_on_error': 120,
    'webui.rss.colenabled': [
      1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    ],
    'webui.rss.colorder': [
      0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25,
      26, 27, 28,
    ],
    'webui.rss.colwidth': [
      200, 100, 60, 100, 100, 100, 60, 60, 60, 60, 60, 60, 60, 80, 100, 90, 200, 100, 100, 100, 60,
      60, 75, 75, 75, 100, 75, 75, 100,
    ],
    'webui.rss.rev': 0,
    'webui.rss.rev2': 0,
    'webui.rss.sindex': -1,
    'webui.rss.sindex2': 0,
    'webui.s2s.colenabled': [1, 1, 1, 1, 1],
    'webui.s2s.colorder': [0, 1, 2, 3, 4],
    'webui.s2s.colwidth': [400, 100, 100, 100, 100],
    'webui.s2s.rev': 0,
    'webui.s2s.rev2': 0,
    'webui.s2s.sindex': -1,
    'webui.s2s.sindex2': 0,
    'webui.search': -1,
    'webui.show_cats': 1,
    'webui.show_dets': 1,
    'webui.show_labelsize': 1,
    'webui.speedintitle': 0,
    'webui.speedlistdl': '100,150,200,250,300,350,400,450,500,750,1000,1250',
    'webui.speedlistul': '100,150,200,250,300,350,400,450,500,750,1000,1250',
    'webui.tasks.colenabled': [1, 1, 1, 1, 1, 1, 1],
    'webui.tasks.colorder': [0, 1, 2, 3, 4, 5, 6],
    'webui.tasks.colwidth': [100, 100, 200, 100, 110, 110, 110],
    'webui.tasks.rev': 0,
    'webui.tasks.rev2': 0,
    'webui.tasks.sindex': -1,
    'webui.tasks.sindex2': 0,
    'webui.teg.colenabled': [
      1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    ],
    'webui.teg.colorder': [
      0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25,
      26, 27, 28,
    ],
    'webui.teg.colwidth': [
      200, 100, 60, 100, 100, 100, 60, 60, 60, 60, 60, 60, 60, 80, 100, 90, 200, 100, 100, 100, 100,
      100, 100, 60, 60, 75, 75, 75, 100,
    ],
    'webui.teg.rev': 0,
    'webui.teg.rev2': 0,
    'webui.teg.sindex': -1,
    'webui.teg.sindex2': 0,
    'webui.timeformat': 0,
    'webui.trk.colenabled': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    'webui.trk.colorder': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    'webui.trk.colwidth': [200, 60, 60, 60, 60, 60, 80, 85, 80, 60],
    'webui.trk.rev': 1,
    'webui.trk.rev2': 0,
    'webui.trk.sindex': 0,
    'webui.trk.sindex2': 0,
    'webui.trt.colenabled': [
      1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1,
    ],
    'webui.trt.colorder': [
      0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25,
      26, 27, 28,
    ],
    'webui.trt.colwidth': [
      439, 74, 60, 94, 100, 100, 60, 101, 72, 60, 60, 60, 82, 80, 100, 90, 200, 100, 100, 100, 100,
      100, 100, 60, 60, 75, 75, 75, 100,
    ],
    'webui.trt.rev': 1,
    'webui.trt.rev2': 0,
    'webui.trt.sindex': -1,
    'webui.trt.sindex2': 0,
    'webui.update_interval': '15000',
    'webui.vsplit': 0.672,
    'webui.xs3.colenabled': [1, 1, 1, 1, 1],
    'webui.xs3.colorder': [0, 1, 2, 3, 4],
    'webui.xs3.colwidth': [400, 150, 100, 100, 100],
    'webui.xs3.rev': 0,
    'webui.xs3.rev2': 0,
    'webui.xs3.sindex': -1,
    'webui.xs3.sindex2': 0,
  }),
});
fetch('https://HOST/rtorrent/php/setsettings.php', {
  headers: {
    accept: 'text/plain, */*; q=0.01',
    authorization: '',
    'content-type': 'application/x-www-form-urlencoded',
    'x-requested-with': 'XMLHttpRequest',
    Referer: 'https://HOST/rtorrent/',
  },
  body: d,
  method: 'POST',
});
```
