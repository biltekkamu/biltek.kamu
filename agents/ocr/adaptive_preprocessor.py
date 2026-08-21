import cv2
import numpy as np

class ImageQualityAnalyzer:
    @staticmethod
    def detect_blur(image: np.ndarray) -> float:
        """حساب درجة ضبابية الصورة باستخدام Laplacian Variance"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())

    @staticmethod
    def detect_contrast_and_brightness(image: np.ndarray):
        """حساب متوسط الإضاءة والتباين"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        mean_brightness = float(np.mean(gray))
        std_contrast = float(np.std(gray))
        return mean_brightness, std_contrast

    @staticmethod
    def detect_skew_angle(image: np.ndarray) -> float:
        """
        حساب زاوية ميلان النصوص بدقة عبر تحليل زوايا الأسطر الحقيقية 
        باستخدام Hough Lines وتجافيها لظلال الخلفية وحواف المستند بشكل آمن
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # 1. إزالة التشويش وتوضيح الحواف
        blur = cv2.GaussianBlur(gray, (9, 9), 0)
        edges = cv2.Canny(blur, 50, 150, apertureSize=3)
        
        # 2. استخراج الخطوط الأفقية
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10)
        
        if lines is None or len(lines) == 0:
            return 0.0

        angles = []
        for line in lines:
            # معالجة آمنة لفك مصفوفة السطر لتجنب خطأ numpy unpack
            line_pts = line.reshape(-1)
            if len(line_pts) >= 4:
                x1, y1, x2, y2 = line_pts[:4]
                angle = np.degrees(np.arctan2(float(y2 - y1), float(x2 - x1)))
                
                # تصفية الزوايا القريبة من المستوى الأفقي (-30 إلى 30 درجة)
                if -30.0 < angle < 30.0:
                    angles.append(angle)

        if not angles:
            return 0.0

        # حساب الوسيط للزوايا الحقيقية
        median_angle = float(np.median(angles))
        return round(median_angle, 2)


class AdaptivePreprocessor:
    @staticmethod
    def apply_clahe(image: np.ndarray) -> np.ndarray:
        """تحسين التباين والإضاءة للنصوص الباهتة والمظلمة"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)

    @staticmethod
    def apply_deskew(image: np.ndarray, angle: float) -> np.ndarray:
        """تعديل واستعادة استقامة الورقة المائلة"""
        if abs(angle) < 0.5:
            return image
            
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated


def process_image_adaptively(image_path: str):
    """
    الدالة التكيفية الرئيسية: تفحص المستند أولاً، ثم تقرر نوع المعالجة المطلوب.
    """
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"تعذر قراءة الصورة من المسار: {image_path}")

    analyzer = ImageQualityAnalyzer()
    preprocessor = AdaptivePreprocessor()

    # 1. تحليل الصورة
    blur_score = analyzer.detect_blur(image)
    brightness, contrast = analyzer.detect_contrast_and_brightness(image)
    skew_angle = analyzer.detect_skew_angle(image)

    applied_filters = []
    processed_image = image.copy()

    # 2. اتخاذ القرار التكيفي (Decision Making)
    
    # فحص التباين والسطوع
    if contrast < 45.0 or brightness < 90.0:
        processed_image = preprocessor.apply_clahe(processed_image)
        applied_filters.append("CLAHE_Contrast_Enhancement")

    # فحص الميلان
    if abs(skew_angle) >= 0.8:
        processed_image = preprocessor.apply_deskew(processed_image, skew_angle)
        applied_filters.append(f"Deskew_{round(skew_angle, 2)}_Degrees")

    if not applied_filters:
        applied_filters.append("None_Image_Is_Clean")

    analysis_report = {
        "blur_score": round(blur_score, 2),
        "brightness": round(brightness, 2),
        "contrast": round(contrast, 2),
        "skew_angle": round(skew_angle, 2),
        "applied_filters": applied_filters
    }

    return processed_image, analysis_report


# --- تجربة التشغيل ---
if __name__ == "__main__":
    sample_path = r"C:\Users\manbe\Downloads\chatbot data\ocr-agent pro\images\test4.jpg"
    
    try:
        _, report = process_image_adaptively(sample_path)
        print("--- تقرير تحليل جودة الصورة النهائي ---")
        print(report)
    except Exception as e:
        print(f"حدث خطأ: {e}")