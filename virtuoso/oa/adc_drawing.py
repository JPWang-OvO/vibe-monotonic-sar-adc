"""ADC-specific functional symbol geometry; called only after electrical pass."""
from html import escape
import math

from .native import q
from .replay import graphic
from virtuoso_bridge.virtuoso.symbol import (
    symbol_create_pin, symbol_create_instance_label, symbol_create_logical_label,
    symbol_create_selection_box, symbol_set_term_order,
)


OUTPUTS = {
    'SAR_PHASE': 'Sample', 'SAR_INV':'Z', 'SAR_DRIVE':'Z', 'SAR_DAC_DRIVE':'Z',
    'SAR_NAND2':'Z', 'SAR_SELECT':'Z', 'SAR_HANDSHAKE':'Z', 'SAR_DONE_DELAY':'Z',
    'SAR_SAMPLE_GUARD2':'Z', 'SAR_WAIT_GATE':'Z', 'SAR_STARTUP':'Hold ClearN',
    'SAR_DFFR':'Q', 'SAR_DFFS':'Q', 'SAR_ARM':'Q', 'SAR_FAST_SEQ':'Q',
    'SAR_CAPTURE_LATCH':'Q QB', 'SAR_OUTPUT_FF':'Q', 'SAR_OUT':'Q',
    'SAR_CMP':'Outp Outn Valid', 'SAR_BIAS':'Bias', 'SAR_BOOST':'Gate', 'SAR_BOOST_HI':'Gate',
    'SAR_SAMPLE':'Gate', 'SAR_BIT':'Q Bp Bn',
    'SAR_ASYNC':'ClkC Done Ck9 Ck8 Ck7 Ck6 Ck5 Ck4 Ck3 Ck2 Ck1 Ck0',
    'MONOTONIC_SAR':'D9 D8 D7 D6 D5 D4 D3 D2 D1 D0 EOC',
}


def direction(cell, port):
    if port in OUTPUTS.get(cell, '').split(): return 'output'
    if cell=='SAR_CMP' and port in ('Vp','Vn','Bias'): return 'input'
    if port in ('VDD','VSS','VREFP','VREFN','VCM','Vin','Vinp','Vinn','Top','Vp','Vn') or port.startswith(('Bp','Bn')):
        return 'inputOutput'
    return 'input'


class Picture:
    def __init__(self, cell, ports, width=2, height=1.5):
        self.cell, self.ports, self.width, self.height = cell, ports, width, height
        self.shapes, self.pins = [], {}

    def line(self, *pts):
        pts=[tuple(round(v*160)/160 for v in p) for p in pts]
        self.shapes.append(dict(type='line',lpp=['device','drawing'],points=[list(p) for p in pts],bbox=[[min(p[0] for p in pts),min(p[1] for p in pts)],[max(p[0] for p in pts),max(p[1] for p in pts)]]))

    def bus(self,*pts):
        self.line(*pts);self.shapes[-1].update(type='path',width=.0125)

    def dot(self,x,y):
        self.line((x-.0125,y),(x+.0125,y))
        self.shapes[-1].update(type='path',width=.025)

    def rect(self,x0,y0,x1,y1):
        self.shapes.append(dict(type='rect',lpp=['device','drawing'],bbox=[[x0,y0],[x1,y1]]))

    def circle(self,x,y,r=.03125):
        self.shapes.append(dict(type='ellipse',lpp=['device','drawing'],bbox=[[x-r,y-r],[x+r,y+r]]))

    def arc(self,bbox,start,stop):
        self.shapes.append(dict(type='arc',lpp=['device','drawing'],bbox=bbox,
                               ellipse_bbox=bbox,angles=[start,stop]))

    def text(self,x,y,label,height=.0625,justify='centerCenter',orient='R0'):
        self.shapes.append(dict(type='label',lpp=['device','drawing'],xy=[x,y],text=label,
            justify=justify,orient=orient,font='stick',height=height,bbox=[[x,y],[x,y]]))

    def block(self,x,y,w,h,label):
        self.rect(x-w/2,y-h/2,x+w/2,y+h/2);self.text(x,y,label)

    def inverter(self,x,y,scale=1):
        w=.1875*scale;h=.125*scale;r=.03125*scale
        self.line((x-w/2,y-h),(x+w/2,y),(x-w/2,y+h),(x-w/2,y-h))
        self.circle(x+w/2+r,y,r)
        return x-w/2,x+w/2+2*r

    def cap(self,x,y):
        self.line((x-.0625,y+.03125),(x+.0625,y+.03125))
        self.line((x-.0625,y-.03125),(x+.0625,y-.03125))
        self.line((x,y+.125),(x,y+.03125));self.line((x,y-.03125),(x,y-.125))

    def switch(self,x,y):
        self.line((x-.125,y),(x-.0625,y),(x+.0625,y+.0625))
        self.line((x+.0625,y),(x+.125,y))

    def pin(self,name,x,y,side,*,label_xy=None,label_orient='R0'):
        self.pins[name]=dict(xy=[x,y],side=side,direction=direction(self.cell,name))
        if label_xy is None:
            label_xy=(x+(.0625 if side in ('left','top','bottom') else -.0625),
                      y+(.0625 if side in ('left','right') else (-.125 if side=='top' else .125)))
        self.pins[name].update(label_xy=list(label_xy),label_orient=label_orient,
                              label_justify='centerRight' if side=='right' else 'centerLeft')

    def boundary(self):
        w,h=self.width/2,self.height/2
        self.rect(-w,-h,w,h)
        for name,p in self.pins.items():
            x,y=p['xy'];side=p['side']
            self.line((x,y),({'left':-w,'right':w}.get(side,x),{'top':h,'bottom':-h}.get(side,y)))


def functional_symbol(data):
    from .adc_functional import draw
    p=draw(data)
    assert set(p.pins)==set(p.ports), (p.cell,set(p.ports)^set(p.pins))
    return p


def symbol_commands(p):
    commands=[graphic(s) for s in p.shapes]
    for name,d in p.pins.items():
        x,y=d['xy'];lx,ly=d['label_xy']
        commands.append(symbol_create_pin(name,x,y,direction=d['direction'],half_size=.0125,
            label_x=lx,label_y=ly,label_justification=d['label_justify'],label_rotation=d['label_orient']))
    commands += [symbol_create_instance_label(0,p.height/2+.1875,justification='centerCenter'),
        symbol_create_logical_label(0,-p.height/2-.1875,text='[@cellName]'),
        symbol_create_selection_box(-p.width/2-.125,-p.height/2-.125,p.width/2+.125,p.height/2+.125),
        symbol_set_term_order(p.ports),f'cv~>portOrder=list({" ".join(q(n) for n in p.ports)})']
    return commands


def svg(p):
    scale=256;w=p.width+1;h=p.height+1.25
    def xy(point):return ((point[0]+w/2)*scale,(h/2-point[1])*scale)
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w*scale:g} {h*scale:g}">',
         '<rect width="100%" height="100%" fill="white"/>',f'<desc>{escape(p.cell)}; terminals follow the accepted Spectre declaration order.</desc>',
         '<g stroke="#287740" stroke-width="1.5" fill="none">']
    texts=[]
    for s in p.shapes:
        if s['type']=='label':texts.append((s['xy'],s['text'],s['height'],{'centerLeft':'start','centerRight':'end'}.get(s['justify'],'middle'),s.get('orient','R0')));continue
        if s['type'] in ('line','path'):
            pts=' '.join(f'{x:g},{y:g}' for x,y in map(xy,s['points']))
            width=f' stroke-width="{s["width"]*scale:g}" stroke-linecap="butt"' if s['type']=='path' else ''
            out.append(f'<polyline points="{pts}"{width}/>')
        elif s['type']=='arc':
            (x0,y0),(x1,y1)=s['ellipse_bbox'];cx,cy=(x0+x1)/2,(y0+y1)/2
            rx,ry=(x1-x0)/2,(y1-y0)/2;a,b=s['angles']
            ax,ay=xy((cx+rx*math.cos(a),cy+ry*math.sin(a)))
            bx,by=xy((cx+rx*math.cos(b),cy+ry*math.sin(b)))
            out.append(f'<path d="M{ax:g},{ay:g} A{rx*scale:g},{ry*scale:g} 0 {int(b-a>math.pi)} 0 {bx:g},{by:g}"/>')
        else:
            (x0,y1),(x1,y0)=map(xy,s['bbox'])
            if s['type']=='rect':out.append(f'<rect x="{x0:g}" y="{y0:g}" width="{x1-x0:g}" height="{y1-y0:g}"/>')
            elif s['type']=='ellipse':out.append(f'<ellipse cx="{(x0+x1)/2:g}" cy="{(y0+y1)/2:g}" rx="{(x1-x0)/2:g}" ry="{(y1-y0)/2:g}"/>')
    out.append('</g><g fill="#287740" font-family="Arial,sans-serif">')
    texts += [([0,p.height/2+.1875],p.cell,.0625,'middle','R0')]
    for point,label,height,anchor,orient in texts:
        x,y=xy(point);rot=f' transform="rotate(-90 {x:g} {y:g})"' if orient=='R90' else ''
        out.append(f'<text x="{x:g}" y="{y:g}" font-size="{height*scale:g}" text-anchor="{anchor}" dominant-baseline="central"{rot}>{escape(label)}</text>')
    out.append('</g><g fill="#c53e32" font-family="Arial,sans-serif" font-size="16">')
    for name,d in p.pins.items():
        x,y=xy(d['xy']);lx,ly=xy(d['label_xy']);side=d['side']
        anchor='end' if d['label_justify']=='centerRight' else 'start'
        rot=f' transform="rotate(-90 {lx:g} {ly:g})"' if d['label_orient']=='R90' else ''
        out.append(f'<g data-port="{escape(name)}" data-side="{side}"><rect x="{x-3.2:g}" y="{y-3.2:g}" width="6.4" height="6.4"/><text x="{lx:g}" y="{ly:g}" text-anchor="{anchor}" dominant-baseline="central"{rot}>{escape(name)}</text></g>')
    out.append('</g></svg>')
    return '\n'.join(out)
