#!/bin/csh
# CAM guide, import tgz (genesis, or d:/tgz)

## Import tgz from Genesis or directory
set tgz_path = $1
set job = $2
set step = $3
set layer = $4
set output_dir = $5
set unit = $6
set dxf_mode = $7

DO_INFO -t job -e $job -m script -d EXISTS
if ($gEXISTS == "yes") then
    VOF
    COM check_inout,mode=out,type=job,job=$job
    COM close_job,job=$job
    COM close_form,job=$job
    COM close_flow,job=$job
    COM delete_entity,job=,type=job,name=$job
    COM close_form,job=$job
    COM close_flow,job=$job
    VON

endif
COM import_job,db=genesis,path=$tgz_path,name=$job,analyze_surfaces=no
COM open_job,job=$job
COM output_layer_reset
COM output_layer_set,layer=outline,angle=0,mirror=no,x_scale=1,y_scale=1,comp=0,polarity=positive,setupfile=,setupfiletmp=,line_units=mm,gscl_file=,step_scale=no
COM output,job=$job,step=$step,format=DXF,dir_path=$output_dir,prefix=,suffix=.dxf,break_sr=yes,break_symbols=yes,break_arc=no,scale_mode=all,surface_mode=contour,min_brush=25.4,units=inch,x_anchor=0,y_anchor=0,x_offset=0,y_offset=0,line_units=mm,override_online=yes,pads_2circles=yes,draft=no,contour_to_hatch=no,pad_outline=no,output_files=single,file_ver=autocad2002,pads_2circles=$dxf_mode
