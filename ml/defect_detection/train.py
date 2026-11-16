"""Train and evaluate the YOLOv8 defect detector.

    python train.py                 # train (use a GPU: Google Colab works well)
    python train.py --eval best.pt  # evaluate a trained model on the validation set
    python train.py --predict best.pt some_photo.jpg

After training, set YOLO_MODEL_PATH in backend/.env to the best.pt file.
"""
import argparse

from ultralytics import YOLO


def train(epochs: int, model: str) -> None:
    yolo = YOLO(model)  # start from COCO-pretrained weights (transfer learning)
    yolo.train(
        data="data.yaml",
        epochs=epochs,
        imgsz=640,
        batch=16,
        patience=20,          # stop early if validation stops improving
        # Augmentation for real station conditions: lighting, angle, blur
        hsv_v=0.4, degrees=5, translate=0.1, scale=0.5, fliplr=0.5,
    )
    metrics = yolo.val()
    print(f"mAP@0.5 = {metrics.box.map50:.3f}   mAP@0.5:0.95 = {metrics.box.map:.3f}   (target mAP@0.5 >= 0.70)")


def evaluate(weights: str) -> None:
    metrics = YOLO(weights).val(data="data.yaml")
    print(f"mAP@0.5 = {metrics.box.map50:.3f}")
    for idx, ap in zip(metrics.box.ap_class_index, metrics.box.ap50):
        print(f"  {metrics.names[int(idx)]:28s} AP@0.5 = {ap:.3f}")


def predict(weights: str, image: str) -> None:
    result = YOLO(weights)(image)[0]
    for box in result.boxes:
        print(result.names[int(box.cls)], round(float(box.conf), 3), [round(v) for v in box.xyxy[0].tolist()])
    result.save(filename="prediction.jpg")
    print("Saved prediction.jpg")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--model", default="yolov8s.pt")
    p.add_argument("--eval", metavar="WEIGHTS")
    p.add_argument("--predict", nargs=2, metavar=("WEIGHTS", "IMAGE"))
    a = p.parse_args()
    if a.eval:
        evaluate(a.eval)
    elif a.predict:
        predict(*a.predict)
    else:
        train(a.epochs, a.model)
