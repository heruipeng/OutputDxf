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

# 全局把 ; 换成空格
# set layers = (`echo $layer | tr ',' ' '`)
# 判断字符串里是否包含 ;
if ( "$layer" =~ *,* ) then
    # 有分号，分割为数组
    set layers = (`echo "$layer" | tr ',' ' '`)
else
    # 无分号，整串作为数组唯一元素
    set layers = ( "$layer" )
endif
echo $layers $job $step $layer $output_dir $unit $dxf_mode
if ($dxf_mode == "yes") then
    echo "\n$dxf_mode"
endif
set min_brush = 25.4
if ($unit == "inch") then
    set min_brush = 1
endif

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

foreach val ($layers)
    if ($dxf_mode == "yes") then
        # 轮廓模式
        COM output_layer_reset
        COM output_layer_set,layer=$val,angle=0,mirror=no,x_scale=1,y_scale=1,comp=0,polarity=positive,setupfile=,setupfiletmp=,line_units=$unit,gscl_file=,step_scale=no
        COM output,job=$job,step=$step,format=DXF,dir_path=$output_dir,prefix=,suffix=.dxf,break_sr=yes,break_symbols=yes,break_arc=no,scale_mode=all,surface_mode=contour,min_brush=$min_brush,units=inch,x_anchor=0,y_anchor=0,x_offset=0,y_offset=0,line_units=$unit,override_online=yes,pads_2circles=yes,draft=no,contour_to_hatch=no,pad_outline=yes,output_files=multiple,file_ver=old
    else
        # 实体模式
        COM output_layer_reset
        COM output_layer_set,layer=$val,angle=0,mirror=no,x_scale=1,y_scale=1,comp=0,polarity=positive,setupfile=,setupfiletmp=,line_units=$unit,gscl_file=,step_scale=no
        COM output,job=$job,step=$step,format=DXF,dir_path=$output_dir,prefix=,suffix=.dxf,break_sr=yes,break_symbols=yes,break_arc=no,scale_mode=all,surface_mode=contour,min_brush=$min_brush,units=inch,x_anchor=0,y_anchor=0,x_offset=0,y_offset=0,line_units=$unit,override_online=yes,pads_2circles=no,draft=no,contour_to_hatch=yes,pad_outline=no,output_files=multiple,file_ver=autocad2002
    endif
end

