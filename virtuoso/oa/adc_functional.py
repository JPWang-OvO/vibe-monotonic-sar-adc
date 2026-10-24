"""Functional drawings derived from the accepted ADC hierarchy.

Ports are placed with their functional objects. Thick lines denote buses;
the top-level output has one native D<9:0> terminal.
"""
import math
from .adc_drawing import Picture


def frame(p):
    p.rect(-p.width/2,-p.height/2,p.width/2,p.height/2)


def port(p,name,xy,side,*route,**labels):
    p.pin(name,*xy,side,**labels)
    if route:p.line(xy,*route)


def supplies(p,x=None):
    x=p.width/2-.25 if x is None else x
    for name,sign,side in [('VDD',1,'top'),('VSS',-1,'bottom')]:
        if name in p.ports:
            y=sign*p.height/2
            port(p,name,(x,y),side,(x,y-sign*.1875))


def dashed(p,a,b):
    length=math.dist(a,b);count=max(1,round(length/.0625))
    for k in range(count):
        p.line(tuple(a[j]+(b[j]-a[j])*k/count for j in (0,1)),
               tuple(a[j]+(b[j]-a[j])*(k+.5)/count for j in (0,1)))


def cap(p,x,y,horizontal=False):
    if horizontal:
        p.line((x-.03125,y-.0625),(x-.03125,y+.0625))
        p.line((x+.03125,y-.0625),(x+.03125,y+.0625))
        p.line((x-.125,y),(x-.03125,y));p.line((x+.03125,y),(x+.125,y))
    else:p.cap(x,y)


def busmark(p,x,y,count):
    p.line((x-.03125,y-.0625),(x+.03125,y+.0625));p.text(x,y+.125,str(count))


def vertical_busmark(p,x,y,count):
    p.line((x-.0625,y-.03125),(x+.0625,y+.03125))
    p.text(x+(.1875 if x>0 else -.1875),y,str(count))


def ground(p,x,y):
    for k,w in enumerate((.125,.075,.025)):p.line((x-w/2,y-k*.0375),(x+w/2,y-k*.0375))


def inv(p,x,y,size=1):
    return p.inverter(x,y,size)


def and_gate(p,x,y,w=.5,h=.5,inverted=False,ys=None):
    """D outline and bubble proportions follow the native ND2 symbol."""
    r=h/2;cx=x+w-r
    p.line((x,y-r),(x,y+r),(cx,y+r))
    p.arc([[cx-r,y-r],[cx+r,y+r]],-math.pi/2,math.pi/2)
    p.line((cx,y-r),(x,y-r))
    out=x+w
    if inverted:p.circle(out+.03125,y);out+=.0625
    ys=ys or [y+h/4,y-h/4]
    for yy in ys:p.line((x-.125,yy),(x,yy))
    return x-.125,out,ys


def or_gate(p,x,y,w=.625,h=.5,inverted=False,ys=None):
    """Curved input and converging output follow the native NR2 silhouette."""
    p.arc([[x-w/3,y-h/2],[x+w/3,y+h/2]],-math.pi/2,math.pi/2)
    p.line((x,y+h/2),(x+w*.5,y+h/2));p.line((x,y-h/2),(x+w*.5,y-h/2))
    def native_point(a,b):return [x+(a-.5625)*w/.375,y+(b-.0625)*h/.25]
    p.arc([native_point(.56875,-.19375),native_point(.95,.1875)],.3529904,1.619997)
    p.arc([native_point(.575,-.0625),native_point(.95,.3125)],-1.637512,-.3430239)
    out=x+w
    if inverted:p.circle(out+.03125,y);out+=.0625
    ys=ys or [y+h/4,y-h/4]
    for yy in ys:
        xx=x+w/3*math.sqrt(1-((yy-y)/(h/2))**2)
        p.line((x-.125,yy),(xx,yy))
    return x-.125,out,ys


def dff(p,x,y,w=.5,h=.625,tag=None):
    p.rect(x-w/2,y-h/2,x+w/2,y+h/2)
    p.line((x-w/2,y-.1875),(x-w/2+.0625,y-.125),(x-w/2,y-.0625))
    if tag:p.text(x,y+.125,tag)


def tg(p,x,y,low=False):
    p.rect(x-.125,y-.0625,x+.125,y+.0625)
    p.text(x,y,'TG')
    if low:p.circle(x,y-.09375)


def bridge_v(p,x,y0,y1,cross):
    """A visible jump distinguishes crossing from a junction."""
    r=.03125;upper=max(y0,y1);lower=min(y0,y1)
    p.line((x,upper),(x,cross+r))
    p.arc([[x-r,cross-r],[x+r,cross+r]],-math.pi/2,math.pi/2)
    p.line((x,cross-r),(x,lower))


def primitive(data):
    n=data['cell'];ports=data['ports']
    if n in ('SAR_DRIVE','SAR_DAC_DRIVE'):
        p=Picture(n,ports,1.5,1);a,z=inv(p,0,0,2)
        port(p,'A',(-.75,0),'left',(a,0));port(p,'Z',(.75,0),'right',(z,0))
        supplies(p,0);return p
    if n in ('SAR_NAND2','SAR_SELECT'):
        p=Picture(n,ports,1.5,1)
        a,z,ys=and_gate(p,-.3125,0,inverted=True)
        for name,y in zip(('A','B'),ys):port(p,name,(-.75,y),'left',(a,y))
        port(p,'Z',(.75,0),'right',(z,0));supplies(p,0);return p
    if n in ('SAR_INV','SAR_HANDSHAKE','SAR_DONE_DELAY'):
        count=3 if n=='SAR_INV' else 2
        p=Picture(n,ports,2.25 if count==3 else 1.75,.875)
        centers=[(i-(count-1)/2)*.625 for i in range(count)]
        ends=[inv(p,x,0) for x in centers]
        port(p,'A',(-p.width/2,0),'left',(ends[0][0],0))
        for a,b in zip(ends,ends[1:]):p.line((a[1],0),(b[0],0))
        port(p,'Z',(p.width/2,0),'right',(ends[-1][1],0))
        supplies(p,0);return p
    if n in ('SAR_DFFR','SAR_DFFS','SAR_ARM','SAR_OUTPUT_FF','SAR_FAST_SEQ'):
        fast=n=='SAR_FAST_SEQ';p=Picture(n,ports,1.75 if fast else 1.5,1.5 if fast else 1.25)
        dff(p,.0625,0,.625,.625,'DFF')
        port(p,'D',(-p.width/2,.1875),'left',(-.25,.1875))
        port(p,'Q',(p.width/2,.1875),'right',(.375,.1875))
        port(p,'CP',(-p.width/2,-.125),'left',(-.25,-.125))
        for name in ('CDN','SDN'):
            if name in ports:
                p.circle(0,-.34375)
                port(p,name,(0,-.625),'bottom',(0,-.375))
                p.text(.1875,-.25,'S' if name=='SDN' else 'R')
        if fast:
            port(p,'CPB',(-.1875,-.75),'bottom',(-.1875,-.3125),label_xy=(-.125,-.6875),label_orient='R90')
            port(p,'Reset',(.1875,-.75),'bottom',(.1875,-.3125),label_xy=(.25,-.6875),label_orient='R90')
            p.text(.1875,-.25,'R')
        supplies(p,p.width/2-.1875);return p
    if n=='SAR_OUT':
        p=Picture(n,ports,2.75,1.25);frame(p);supplies(p)
        dff(p,-.625,0,tag='DFF')
        port(p,'D',(-1.375,.1875),'left',(-.875,.1875))
        port(p,'Done',(-1.375,-.125),'left',(-.875,-.125))
        a,z=inv(p,.125,.1875);b,q=inv(p,.75,.1875)
        p.line((-.375,.1875),(a,.1875));p.line((z,.1875),(b,.1875))
        port(p,'Q',(1.375,.1875),'right',(q,.1875));return p
    if n=='SAR_CAPTURE_LATCH':
        p=Picture(n,ports,2.25,1.5);frame(p);supplies(p)
        tg(p,-.75,.125,low=True);tg(p,-.25,.5)
        a,b=inv(p,-.1875,.125);c,d=inv(p,.4375,.125)
        port(p,'D',(-1.125,.125),'left',(-.875,.125))
        p.line((-.625,.125),(a,.125));p.line((b,.125),(c,.125))
        port(p,'Q',(1.125,.125),'right',(d,.125))
        p.line((.75,.125),(.75,.5),(-.125,.5));p.dot(.75,.125)
        p.line((-.375,.5),(-.5,.5),(-.5,.125));p.dot(-.5,.125)
        p.line((.125,.125),(.125,-.375),(1.125,-.375));p.dot(.125,.125)
        p.pin('QB',1.125,-.375,'right')
        port(p,'Hold',(-.75,-.75),'bottom',(-.75,0),label_xy=(-.6875,-.625))
        p.line((-.25,.4375),(-.25,.375));p.text(-.0625,.375,'Hold')
        return p
    if n=='SAR_BIAS':
        p=Picture(n,ports,1.5,1.5)
        port(p,'VDD',(0,.75),'top',(0,.4375))
        p.line((0,.4375),(.0625,.4375),(.0625,.125),(0,.125),(0,.0625))
        p.line((-.125,.375),(-.125,.1875));p.circle(-.15625,.28125)
        p.line((-.1875,.28125),(-.375,.28125),(-.375,.0625),(0,.0625));p.dot(0,.0625)
        port(p,'Bias',(.75,.0625),'right',(0,.0625))
        p.circle(0,-.25,.125);p.line((0,.0625),(0,-.125));p.line((0,-.375),(0,-.75))
        p.line((0,-.1875),(0,-.3125));p.line((-.0375,-.275),(0,-.3125),(.0375,-.275))
        p.pin('VSS',0,-.75,'bottom');p.text(-.3125,-.25,'I bias')
        cap(p,.375,-.25);p.line((.375,-.125),(.375,.0625));p.dot(.375,.0625)
        p.line((.375,-.375),(.375,-.5625),(0,-.5625));p.dot(0,-.5625)
        return p


def small_logic(data):
    n=data['cell'];p=Picture(n,data['ports'],3.5 if n=='SAR_WAIT_GATE' else 2.25,1.875 if n=='SAR_WAIT_GATE' else 1.25)
    frame(p);supplies(p)
    if n=='SAR_SAMPLE_GUARD2':
        a,b=inv(p,-.5,.1875);c,d=inv(p,-.0625,.1875)
        x,z,ys=or_gate(p,.3125,0,.5,.5)
        port(p,'A',(-1.125,0),'left',(-.875,0))
        p.line((-.875,0),(-.875,.1875),(a,.1875));p.line((b,.1875),(c,.1875))
        p.line((d,.1875),(.1875,.1875),(.1875,.125));p.line((-.875,0),(-.875,-.125),(x,-.125));p.dot(-.875,0)
        port(p,'Z',(1.125,0),'right',(z,0));p.text(-.3125,.4375,'delay + C')
        return p
    if n=='SAR_WAIT_GATE':
        a,z,ys=or_gate(p,-.25,.1875,1.25,1,inverted=True,ys=[.5625,.3125,.0625,-.1875])
        for name,y in zip(('Hold','Valid','Done'),ys):port(p,name,(-1.75,y),'left',(a,y))
        b,c,ins=and_gate(p,-1,-.5625,.5,.5)
        for name,y in zip(('Delayed','Early'),ins):port(p,name,(-1.75,y),'left',(b,y))
        p.line((c,-.5625),(a,-.5625),(a,-.1875))
        port(p,'Z',(1.75,.1875),'right',(z,.1875));return p
    raise ValueError(n)


def startup(data):
    p=Picture(data['cell'],data['ports'],3,2.25);frame(p);supplies(p)
    p.block(-.75,.8125,.625,.25,'POR')
    dff(p,-.75,0,.5,.75,'ARM');p.circle(-.75,.40625)
    p.line((-.75,.4375),(-.75,.6875))
    p.line((-1,.1875),(-1.1875,.1875));p.text(-1.1875,.3125,'1')
    port(p,'Sample',(-1.5,-.125),'left',(-1,-.125))
    a,b=inv(p,-.125,.25);p.line((-.5,.25),(a,.25))
    x,z,ys=or_gate(p,.375,.375,.5,.5)
    p.line((b,.25),(x,.25));port(p,'Guard',(-1.5,.5),'left',(x,.5))
    port(p,'Hold',(1.5,.375),'right',(z,.375))
    u,v,ins=and_gate(p,.375,-.375,.5,.5)
    p.line((-.375,.25),(-.375,-.25),(u,-.25));p.dot(-.375,.25)
    a,b=inv(p,-.75,-.5)
    p.line((-1.25,-.125),(-1.25,-.5),(a,-.5));p.dot(-1.25,-.125)
    p.line((b,-.5),(u,-.5));port(p,'ClearN',(1.5,-.375),'right',(v,-.375))
    return p


def draw(data):
    n=data['cell']
    if n in ('SAR_SAMPLE_GUARD2','SAR_WAIT_GATE'):return small_logic(data)
    if n=='SAR_STARTUP':return startup(data)
    p=primitive(data)
    if p:return p
    return COMPLEX[n](data)


def comparator(data):
    p=Picture(data['cell'],data['ports'],4.25,2);frame(p);supplies(p)
    p.line((-1.5,-.5),(-1.5,.75),(-.5,.125),(-1.5,-.5))
    for name,y,sign in [('Vp',.375,'+'),('Vn',-.125,'-')]:
        port(p,name,(-2.125,y),'left',(-1.5,y));p.text(-1.375,y,sign,.09375)
        ends=[inv(p,x,y) for x in (-.25,.5,1)]
        p.line((-.9,y),(ends[0][0],y))
        for a,b in zip(ends,ends[1:]):p.line((a[1],y),(b[0],y))
        port(p,'Outp' if name=='Vp' else 'Outn',(2.125,y),'right',(ends[-1][1],y))
    p.text(-1.1875,.125,'regen');p.text(-1.25,.5625,'PMOS')
    port(p,'Bias',(-2.125,-.625),'left',(-1.25,-.625),(-1.25,-.34375))
    port(p,'ClkC',(-1,-1),'bottom',(-1,-.1875),label_xy=(-.9375,-.875),label_orient='R90')
    a,z,ys=and_gate(p,.5,-.625,.375,.5,inverted=True)
    bridge_v(p,.125,.375,-.5,-.125);p.dot(.125,.375);p.line((.125,-.5),(a,-.5))
    p.line((0,-.125),(0,-.75),(a,-.75));p.dot(0,-.125)
    b,c=inv(p,1.125,-.625);d,e=inv(p,1.5,-.625)
    p.line((z,-.625),(b,-.625));p.line((c,-.625),(d,-.625))
    port(p,'Valid',(2.125,-.625),'right',(e,-.625))
    return p


def cdac(data):
    p=Picture(data['cell'],data['ports'],3,2.75);frame(p)
    for sign,prefix,top in [(-1,'Bp','Vp'),(1,'Bn','Vn')]:
        rail=sign*.1875;x=sign*.625
        port(p,top,(rail,1.375),'top',(rail,-.9375))
        for bit in range(9,0,-1):
            y=.75-(9-bit)*.1875;cap(p,x,y,True)
            p.line((x+sign*.125,y),(sign*1,y),(sign*1.0625,y+.0625))
            p.line((x-sign*.125,y),(rail,y));p.dot(rail,y)
            p.text(sign*.375,y+.0625,str(2**(bit-1)))
        p.bus((sign*1.0625,-.6875),(sign*1.0625,.9375),(sign*1.5,.9375))
        port(p,prefix+'<9:1>',(sign*1.5,.9375),'left' if sign<0 else 'right')
        vertical_busmark(p,sign*1.0625,-.25,9)
        cap(p,x,-.9375,True);p.line((x-sign*.125,-.9375),(rail,-.9375))
        p.text(sign*.375,-.875,'1')
        p.line((x+sign*.125,-.9375),(sign*1,-.9375),(sign*1,-1.125),(0,-1.125))
    port(p,'VREFP',(0,-1.375),'bottom',(0,-1.125));p.dot(0,-1.125)
    port(p,'VREFN',(-.875,-1.375),'bottom',(-.875,-1.1875))
    p.line((-.90625,-1.21875),(-.84375,-1.15625));p.line((-.90625,-1.15625),(-.84375,-1.21875))
    p.text(0,1,'512 C / side')
    return p


def boost(data):
    p=Picture(data['cell'],data['ports'],2.5,1.75);frame(p)
    # Cb follows Vin during tracking; Ct is precharged, then transferred to Gate.
    cap(p,0,.25,True);p.text(0,.5,'Cboot')
    p.switch(-.625,.25);p.switch(.625,.25)
    port(p,'Vin',(-1.25,.25),'left',(-.75,.25))
    p.line((-.5,.25),(-.125,.25));p.line((.125,.25),(.5,.25))
    port(p,'Gate',(1.25,.25),'right',(.75,.25))
    p.text(-.625,.4375,'Gate' if data['cell']=='SAR_BOOST' else 'SampleB')
    p.text(.625,.4375,'track')
    # Precharge path from VDD enters the upper plate directly.
    port(p,'VDD',(.25,.875),'top',(.25,.6875))
    p.line((.25,.6875),(.25,.625),(.3125,.5));p.circle(.25,.625,.0125);p.circle(.25,.4375,.0125)
    p.line((.25,.4375),(.25,.25));p.dot(.25,.25);p.text(.5,.625,'reset')
    for x in (-.3125,.9375):
        p.line((x,.25),(x,-.0625));p.circle(x,-.0625,.0125)
        p.line((x,-.125),(x+.0625,-.25));p.circle(x,-.3125,.0125)
        p.line((x,-.3125),(x,-.4375));ground(p,x,-.4375);p.dot(x,.25)
        p.text(x+.1875,-.1875,'SB')
    port(p,'Sample',(-1.25,-.4375),'left',(-.875,-.4375));p.text(-.75,-.4375,'S')
    port(p,'SampleB',(-1.25,-.6875),'left',(-.875,-.6875));p.text(-.75,-.6875,'SB')
    port(p,'VSS',(1,-.875),'bottom',(1,-.6875))
    p.text(.1875,-.6875,'S: track   SB: reset')
    return p


def sample(data):
    p=Picture(data['cell'],data['ports'],2.75,1.75);frame(p);supplies(p)
    # Horizontal NMOS conduction path; gate comes straight up from the boost.
    port(p,'Vin',(-1.375,.375),'left',(.25,.375))
    p.line((.25,.375),(.25,.3125),(.5,.3125),(.5,.375))
    p.line((.25,.1875),(.5,.1875));p.line((.375,.1875),(.375,-.1875))
    port(p,'Top',(1.375,.375),'right',(.5,.375))
    p.text(.375,.5625,'NMOS')
    p.block(-.375,-.1875,1.5,.375,'')
    for x in (-.75,-.125):
        cap(p,x,-.1875,True);p.text(x,-.4375,'boot 1' if x==-.75 else 'boot 2')
    p.line((-1.125,-.1875),(-.875,-.1875));p.line((-.625,-.1875),(-.25,-.1875));p.line((0,-.1875),(.375,-.1875))
    p.line((-1.1875,.375),(-1.1875,-.1875),(-1.125,-.1875));p.dot(-1.1875,.375)
    port(p,'Gate',(1.375,-.1875),'right',(.375,-.1875));p.dot(.375,-.1875)
    for name,x in [('Sample',-.875),('SampleB',-.375)]:
        port(p,name,(x,-.875),'bottom',(x,-.375),label_xy=(x+.0625,-.8125),label_orient='R90')
    cap(p,.875,.125);p.line((.875,.25),(.875,.375));p.dot(.875,.375)
    p.line((.875,0),(.875,-.0625));p.text(.875,-.125,'VDD');p.text(.6875,.125,'Cj')
    return p


def bitcell(data):
    p=Picture(data['cell'],data['ports'],3,1.75);frame(p)
    port(p,'VDD',(-1.25,.875),'top',(-1.25,.6875));port(p,'VSS',(1.25,-.875),'bottom',(1.25,-.6875))
    p.block(-.6875,.25,.625,.625,'latch')
    port(p,'Outp',(-1.5,.375),'left',(-1,.375))
    port(p,'Capture',(-.6875,-.875),'bottom',(-.6875,-.125),label_xy=(-.625,-.75),label_orient='R90')
    p.circle(-.6875,-.09375);p.text(-.6875,.0625,'EN')
    # Captured Q and QB drive separate NAND selections and tapered drivers.
    for y,out in [(.375,'Bp'),(-.125,'Bn')]:
        a,z,ys=and_gate(p,0,y,.375,.375,inverted=True)
        if out=='Bp':
            p.line((-.375,.375),(-.25,.375),(-.25,ys[0]),(a,ys[0]))
            p.line((-.25,.375),(-.25,.6875),(1.5,.6875));p.dot(-.25,.375)
            p.pin('Q',1.5,.6875,'right')
        else:
            p.line((-.375,.125),(-.3125,.125),(-.3125,ys[0]),(a,ys[0]))
        p.line((-.1875,ys[1]),(a,ys[1]))
        b,c=inv(p,.625,y);d,e=inv(p,1,y)
        p.line((z,y),(b,y));p.line((c,y),(d,y));port(p,out,(1.5,y),'right',(e,y))
    p.dot(-.6875,-.4375)
    p.line((-.6875,-.4375),(-.1875,-.4375))
    bridge_v(p,-.1875,-.4375,.28125,-.03125)
    port(p,'VREFP',(.5,.875),'top',(.5,.75));port(p,'VREFN',(.5,-.875),'bottom',(.5,-.6875))
    # Sample is a retained but unused interface; Capture controls precharge.
    port(p,'Sample',(-1.5,-.4375),'left',(-1.125,-.4375))
    p.line((-1.15625,-.46875),(-1.09375,-.40625));p.line((-1.15625,-.40625),(-1.09375,-.46875))
    p.text(.625,-.5625,'reference drive')
    return p


def phase(data):
    p=Picture(data['cell'],data['ports'],3.75,1.875);frame(p);supplies(p)
    p.block(-1.375,.5,.625,.25,'POR')
    p.block(-1.375,-.375,.5,.375,'gate')
    p.line((-1.375,.375),(-1.375,-.1875))
    port(p,'Clks',(-1.875,-.375),'left',(-1.625,-.375))
    p.line((-1.125,-.375),(1,-.375))
    for i in range(5):
        x=-.75+i*.4375;p.block(x,.125,.25,.375,'R'+str(i))
        p.line((x,-.375),(x,-.0625));p.dot(x,-.375)
        p.line((x-.03125,-.0625),(x,0),(x+.03125,-.0625))
        if i<4:p.line((x+.125,.1875),(x+.3125,.1875))
    p.line((1.125,.1875),(1.3125,.1875),(1.3125,.6875),(-.9375,.6875),(-.9375,.1875),(-.875,.1875))
    p.text(.1875,.8125,'00001')
    p.line((-.625,.1875),(-.5625,.1875));p.dot(-.5625,.1875)
    bridge_v(p,-.5625,.1875,-.625,-.375)
    a,b=inv(p,.125,-.625);c,d=inv(p,.875,-.625)
    p.line((-.5625,-.625),(a,-.625));p.line((b,-.625),(c,-.625))
    port(p,'Sample',(1.875,-.625),'right',(d,-.625))
    p.text(.5,-.8125,'6-stage drive')
    return p


def async_control(data):
    p=Picture(data['cell'],data['ports'],4,3);frame(p);supplies(p)
    # Three representative stages retain the shift direction and common clock.
    for i,(x,label) in enumerate([(-.75,'9'),(0,'8'),(.75,'0')]):
        p.block(x,.5,.375,.5,label)
        p.line((x,.0625),(x,.25));p.dot(x,.0625)
        p.line((x-.03125,.25),(x,.3125),(x+.03125,.25))
        p.line((x-.125,.75),(x-.125,.9375));p.text(x-.125,1,'R')
        q=x+.1875
        p.line((q,.5),(q+.0625,.5),(q+.0625,1.0625),(q+.125,1.125))
    p.line((-.9375,.5),(-1.125,.5));p.text(-1.125,.6875,'1')
    p.line((-.5625,.5),(-.1875,.5))
    p.line((.1875,.5),(.3125,.5));p.text(.4375,.5,'...');p.line((.5,.5),(.5625,.5))
    p.bus((-.5,1.125),(2,1.125));busmark(p,1.25,1.125,10)
    port(p,'Ck<9:0>',(2,1.125),'right')
    port(p,'Valid',(-2,.0625),'left',(.75,.0625))
    p.block(-1.25,-.75,.75,.5,'start / reset')
    port(p,'Sample',(-2,-.75),'left',(-1.625,-.75))
    p.line((-1.25,-.5),(-1.25,-.375));p.text(-1.0625,-.375,'R')
    p.block(-1.25,-.1875,.625,.25,'delay')
    p.line((-1.75,.0625),(-1.75,-.1875),(-1.5625,-.1875));p.dot(-1.75,.0625)
    p.block(-.25,-.875,.875,.375,'wait')
    p.line((-.875,-.75),(-.6875,-.75))
    p.line((-.9375,-.1875),(-.25,-.1875),(-.25,-.6875))
    bridge_v(p,-.5,.0625,-.6875,-.1875);p.dot(-.5,.0625)
    p.line((.0625,-.6875),(.0625,-.5));p.text(.0625,-.4375,'Ck<5>')
    p.line((.9375,.5),(1.125,.5),(1.125,-.625),(.3125,-.625),(.3125,-.8125),(.1875,-.8125));p.dot(.9375,.5)
    p.block(.75,-.875,.75,.25,'delay')
    p.line((.75,-.625),(.75,-.75));p.dot(.75,-.625)
    port(p,'Done',(.75,-1.5),'bottom',(.75,-1),label_xy=(.8125,-1.375))
    p.line((-.25,-1.0625),(-.25,-1.125))
    p.line((-.375,-1.125),(-.125,-1.125),(-.25,-1.3125),(-.375,-1.125))
    p.circle(-.25,-1.34375)
    port(p,'ClkC',(-.25,-1.5),'bottom',(-.25,-1.375),label_xy=(-.1875,-1.4375))
    return p


def frontend(data):
    p=Picture(data['cell'],data['ports'],3.75,3.5);frame(p);supplies(p)
    p.rect(-1.25,.625,-.75,1.375);p.text(-1,.6875,'boot')
    for name,x in [('Sample',-1.125),('SampleB',-.875)]:
        port(p,name,(x,1.75),'top',(x,1.375),label_xy=(x+.0625,1.4375),label_orient='R90')
    for vin,vout,y,gate in [('Vinp','Vp',1.125,'Gp'),('Vinn','Vn',.8125,'Gn')]:
        p.switch(-1,y)
        port(p,vin,(-1.875,y),'left',(-1.125,y))
        port(p,vout,(1.875,y),'right',(-.875,y))
        p.text(-1,y+.1875,gate)
    # The two charge-injection compensation capacitors connect to opposite tops.
    for x,gate in [(0,'Gn'),(.5,'Gp')]:
        cap(p,x,1.4375);p.text(x,1.625,gate)
    p.line((0,1.3125),(0,1.125));p.dot(0,1.125)
    bridge_v(p,.5,1.3125,.8125,1.125);p.dot(.5,.8125);p.text(.75,1.4375,'Cx')
    port(p,'VREFP',(1,1.75),'top',(1,1.5));p.text(1,1.4375,'VR')
    bridge_v(p,-.25,1.125,-1.4375,.8125);p.dot(-.25,1.125)
    p.line((.25,.8125),(.25,-1.4375));p.dot(.25,.8125)
    for sign,prefix in [(-1,'Bp'),(1,'Bn')]:
        for bit in range(9,0,-1):
            y=.25-(9-bit)*.1875;x=sign*.875;cap(p,x,y,True)
            p.line((x+sign*.125,y),(sign*1.3125,y),(sign*1.375,y+.0625))
            p.line((x-sign*.125,y),(sign*.25,y));p.dot(sign*.25,y)
            p.text(sign*.5,y+.0625,str(2**(bit-1)))
        p.bus((sign*1.375,-1.1875),(sign*1.375,.4375),(sign*1.875,.4375))
        port(p,prefix+'<9:1>',(sign*1.875,.4375),'left' if sign<0 else 'right')
        vertical_busmark(p,sign*1.375,-.625,9)
        cap(p,sign*.875,-1.4375,True)
        p.line((sign*.75,-1.4375),(sign*.25,-1.4375));p.text(sign*.5,-1.375,'1')
        p.line((sign*1,-1.4375),(sign*1.25,-1.4375),(sign*1.25,-1.5625),(0,-1.5625))
    p.text(0,-1.6875,'VR')
    port(p,'VREFN',(.75,-1.75),'bottom',(.75,-1.625))
    p.line((.71875,-1.65625),(.78125,-1.59375));p.line((.71875,-1.59375),(.78125,-1.65625))
    return p


def adc(data):
    p=Picture(data['cell'],data['ports'],6,3);frame(p);supplies(p)
    p.block(-2,.5625,.5,.75,'S/H')
    for name,y in [('Vinp',.75),('Vinn',.375)]:
        port(p,name,(-3,y),'left',(-2.125,y));p.switch(-2,y)
        p.line((-1.875,y),(-1.25,y))
    p.block(-.875,.5625,.75,.75,'CDAC')
    p.line((-.125,.1875),(-.125,.9375),(.625,.5625),(-.125,.1875))
    for y,sign in [(.75,'+'),(.375,'-')]:
        p.line((-.5,y),(-.125,y));p.text(0,y,sign,.09375)
    p.block(1,.5625,.625,.75,'10 latches')
    p.line((.625,.5625),(.6875,.5625))
    p.block(1.875,.5625,.5,.75,'10 FF')
    p.bus((1.3125,.5625),(1.625,.5625));busmark(p,1.46875,.5625,10)
    p.bus((2.125,.5625),(3,.5625));busmark(p,2.5,.5625,10)
    port(p,'D<9:0>',(3,.5625),'right')
    # Bottom-plate selection returns above the analog path; clocks stay below it.
    p.bus((1,.9375),(1,1.1875),(-.875,1.1875),(-.875,.9375))
    busmark(p,.5,1.1875,18);p.text(-.1875,1.3125,'bottom plates')
    p.block(.25,-.5,1.75,.5,'asynchronous control')
    p.line((.25,-.25),(.25,.375));p.text(.3125,-.125,'ClkC',orient='R90')
    p.line((.5,.5),(.5,-.25));p.text(.5625,-.125,'Valid',orient='R90')
    p.bus((1,-.25),(1,.1875));busmark(p,1,-.0625,10)
    p.line((.9375,.1875),(1,.25),(1.0625,.1875))
    p.line((1.125,-.5),(1.875,-.5),(1.875,.1875));p.dot(1.875,-.5)
    p.line((1.8125,.1875),(1.875,.25),(1.9375,.1875))
    port(p,'EOC',(3,-1.125),'right',(1.875,-1.125),(1.875,-.5))
    p.block(-2,-.875,.5,.375,'/5')
    port(p,'Clks',(-3,-.875),'left',(-2.25,-.875))
    p.line((-2,-.6875),(-2,.1875));p.text(-1.9375,-.3125,'Sample',orient='R90')
    p.line((-1.75,-.875),(-1.5,-.875),(-1.5,-.5),(-.625,-.5))
    port(p,'VREFP',(-1.5,1.5),'top',(-1.5,1.3125))
    port(p,'VREFN',(-1.5,-1.5),'bottom',(-1.5,-1.3125))
    port(p,'VCM',(-2.5,1.5),'top',(-2.5,1.3125))
    p.line((-2.53125,1.28125),(-2.46875,1.34375));p.line((-2.53125,1.34375),(-2.46875,1.28125))
    return p


COMPLEX={'SAR_CMP':comparator,'SAR_CDAC':cdac,'SAR_BOOST':boost,'SAR_BOOST_HI':boost,
         'SAR_SAMPLE':sample,'SAR_BIT':bitcell,'SAR_PHASE':phase,'SAR_ASYNC':async_control,
         'SAR_FRONTEND':frontend,'MONOTONIC_SAR':adc}
