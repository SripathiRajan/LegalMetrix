from app.models.extracted_product import OCRRegion
from app.vision.reading_order import ReadingOrderResolver



# 1. Test Angle Computation on 4-Point Polygons
def test_compute_polygon_angle():
    # 0 degrees: horizontal left-to-right
    bbox_0 = [[10, 10], [100, 10], [100, 30], [10, 30]]
    assert ReadingOrderResolver.compute_polygon_angle(bbox_0) == 0.0

    # 90 degrees: vertical downwards (rotated 90° clockwise)
    bbox_90 = [[100, 10], [100, 100], [80, 100], [80, 10]]
    assert ReadingOrderResolver.compute_polygon_angle(bbox_90) == 90.0

    # 180 degrees: right-to-left upside down
    bbox_180 = [[100, 30], [10, 30], [10, 10], [100, 10]]
    assert ReadingOrderResolver.compute_polygon_angle(bbox_180) == 180.0

    # 270 degrees: vertical upwards (rotated 270° clockwise / 90° counter-clockwise)
    bbox_270 = [[80, 100], [80, 10], [100, 10], [100, 100]]
    assert ReadingOrderResolver.compute_polygon_angle(bbox_270) == 270.0

    # Standard axis-aligned [xmin, ymin, xmax, ymax]
    assert ReadingOrderResolver.compute_polygon_angle([10, 10, 100, 30]) == 0.0


# 2. Test Synthetic Mixed Upright + 90°-Rotated Non-Interleaved Ordering
def test_mixed_upright_and_rotated_non_interleaved():
    """
    Simulates a product label with:
      - Upright text lines on the left panel (0° angle)
      - A vertical sidebar barcode / batch metadata panel rotated 90°
    The reading order resolver must cluster them into distinct blocks and
    produce a clean, non-interleaved sequence.
    """
    # Upright regions (left side, horizontal 0°)
    upright_1 = OCRRegion(
        text="Brand Crunchy Biscuits",
        confidence=0.98,
        bounding_box=[[20, 20], [200, 20], [200, 45], [20, 45]]
    )
    upright_2 = OCRRegion(
        text="Net Quantity: 200 g",
        confidence=0.96,
        bounding_box=[[20, 55], [160, 55], [160, 75], [20, 75]]
    )
    upright_3 = OCRRegion(
        text="MRP: Rs. 60.00 (incl. taxes)",
        confidence=0.97,
        bounding_box=[[20, 85], [220, 85], [220, 105], [20, 105]]
    )

    # 90°-rotated sidebar regions (right side, vertical 90°)
    # Top edge p0->p1 points downwards along y-axis (dx=0, dy=100)
    rotated_sidebar_1 = OCRRegion(
        text="BATCH NO: B-9981",
        confidence=0.94,
        bounding_box=[[400, 20], [400, 120], [375, 120], [375, 20]]
    )
    rotated_sidebar_2 = OCRRegion(
        text="EXP: 12/2026",
        confidence=0.95,
        bounding_box=[[430, 20], [430, 120], [405, 120], [405, 20]]
    )

    # Pass in shuffled order
    shuffled_regions = [
        rotated_sidebar_1,
        upright_2,
        rotated_sidebar_2,
        upright_1,
        upright_3
    ]

    resolver = ReadingOrderResolver()
    resolved = resolver.resolve(shuffled_regions, img_width=500, img_height=300)

    assert len(resolved) == 5
    resolved_texts = [r.text for r in resolved]

    # Verify upright text is read top-to-bottom without interruption
    upright_indices = [
        resolved_texts.index("Brand Crunchy Biscuits"),
        resolved_texts.index("Net Quantity: 200 g"),
        resolved_texts.index("MRP: Rs. 60.00 (incl. taxes)")
    ]
    # Indices must be strictly monotonic (0, 1, 2)
    assert upright_indices[0] < upright_indices[1] < upright_indices[2]

    # Verify rotated sidebar text is grouped and ordered without being interleaved
    sidebar_indices = [
        resolved_texts.index("BATCH NO: B-9981"),
        resolved_texts.index("EXP: 12/2026")
    ]
    assert sidebar_indices[0] < sidebar_indices[1]

    # Check non-interleaved block structure
    # Either all upright regions come first, then all sidebar regions, or vice versa
    is_upright_first = max(upright_indices) < min(sidebar_indices)
    is_sidebar_first = max(sidebar_indices) < min(upright_indices)
    assert is_upright_first or is_sidebar_first, f"Ordering was interleaved: {resolved_texts}"

    # Verify annotations on resolved regions
    for r in resolved:
        assert r.cluster_id is not None
        assert r.reading_order_confidence is not None
        if "Biscuits" in r.text or "Net" in r.text or "MRP" in r.text:
            assert r.detected_angle_degrees == 0.0
            assert "horiz" in r.cluster_id
        else:
            assert r.detected_angle_degrees == 90.0
            assert "vert" in r.cluster_id


# 3. Test Standalone Invocation and Empty / Single Region Edge Cases
def test_reading_order_resolver_edge_cases():
    resolver = ReadingOrderResolver()

    # Empty
    assert resolver.resolve([]) == []

    # Single region
    single = OCRRegion(
        text="Single Line",
        confidence=0.99,
        bounding_box=[[10, 10], [50, 10], [50, 30], [10, 30]]
    )
    res = resolver.resolve([single])
    assert len(res) == 1
    assert res[0].text == "Single Line"
    assert res[0].detected_angle_degrees == 0.0
    assert res[0].cluster_id is not None
