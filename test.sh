CUDA_VISIBLE_DEVICES=1 python3 -u tools/test.py configs/_xm/faster_rcnn_r50_fpn_diou.py  work_dirs/faster_rcnn_r50_fpn_diou/epoch_4.pth --get_roi --eval mAP