"""Render the accepted ADC's editable SVG symbols with Inkscape."""
import argparse
from pathlib import Path
import shutil
import subprocess

from PIL import Image
from regression.common.project import ROOT,artifact_root,read_json,write_json
from .adc_source import source_folders,reference_libraries


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--inkscape',default=shutil.which('inkscape'));args=parser.parse_args()
    assert args.inkscape,'Specify the installed Inkscape executable'
    folders=source_folders();references=reference_libraries()
    output=artifact_root()/'oa_delivery/symbol_previews';output.mkdir(exist_ok=True,parents=True)
    actions=[];images=[]
    for name,folder in sorted(folders.items()):
        if name in references or name.startswith('tb_'):continue
        source=folders[name]/'symbol/functional.svg'
        target=output/(name+'.png');images.append(target)
        actions.extend(['file-open:'+source.as_posix(),'export-filename:'+target.as_posix(),
                        'export-type:png','export-do','file-close'])
    action_file=output/'render-actions.txt';action_file.write_text(';'.join(actions),encoding='utf-8')
    result=subprocess.run([args.inkscape,'--batch-process','--actions-file='+str(action_file)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    write_json(output/'images.json',[str(p) for p in images])
    for start in range(0,len(images),4):
        sheet=Image.new('RGB',(1800,1200),'white')
        for index,path in enumerate(images[start:start+4]):
            im=Image.open(path);im.thumbnail((880,580))
            sheet.paste(im,((index%2)*900+(900-im.width)//2,(index//2)*600+(600-im.height)//2))
        sheet.save(output/f'gallery_{start//4+1}.png')
    print('Rendered',len(images),'SVGs in',output)


if __name__=='__main__':main()
